"""Extract step of the ELT pipeline.

Pulls recent commits for a hardcoded GitHub repository via the GitHub REST
API and uploads the raw JSON response to an S3 bucket (under the `raw/`
prefix) for later ingestion into Snowflake by the dbt layer
(see transform/my_pipeline/models/stg_commits.sql).

Inputs (environment variables, loaded from a local `.env` file via
python-dotenv, or injected by Docker/Airflow):
    GITHUB_TOKEN            - GitHub personal access token
    AWS_BUCKET              - destination S3 bucket name
    AWS_ACCESS_KEY_ID       - AWS access key
    AWS_SECRET_ACCESS_KEY   - AWS secret key

Output:
    An object written to `s3://$AWS_BUCKET/raw/commits_<YYYYMMDD>.json`
    containing the raw list of GitHub commit objects as returned by the
    API (no transformation applied here).

Invoked as a script (`python src/extract.py`) by the `extract_github_data`
task in airflow/dags/elt_dag.py.
"""
import os
import requests
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv
from urllib3.util.retry import Retry
load_dotenv()
# Load secrets from Environment Variables (Docker will provide these)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
AWS_BUCKET = os.getenv('AWS_BUCKET')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Pipeline tuning constants. These are currently hardcoded rather than
# environment-driven; see .env.example / README for the reproducibility note.
DEFAULT_REPO_OWNER = 'apache'
DEFAULT_REPO_NAME = 'airflow'
MAX_PAGES = 5          # Fetch at most 5 pages (~150 commits) per run
PER_PAGE = 30          # GitHub API results per page
MAX_CONNECTION_RETRIES = 3  # Retries for the underlying HTTP connection (see note below)
RETRY_BACKOFF_FACTOR = 1.0  # Seconds; urllib3 sleeps backoff_factor * (2 ** (retry_count - 1))
# HTTP status codes worth retrying: 429 (explicit rate limit) and 5xx (transient
# server errors). Deliberately excludes GitHub's 403, which is used for BOTH
# rate-limit responses and genuine permission/auth failures (e.g. a bad token)
# that retrying would never fix — forcing retries there would just waste time
# on a broken token.
RETRYABLE_STATUS_CODES = [429, 500, 502, 503, 504]


def get_commits(repo_owner: str, repo_name: str) -> list[dict]:
    """Fetch recent commits for a GitHub repository.

    Pages through the GitHub "list commits" REST API up to MAX_PAGES pages
    of PER_PAGE commits each, stopping early if a page comes back empty.

    Args:
        repo_owner: GitHub organization/user that owns the repo (e.g. "apache").
        repo_name: Repository name (e.g. "airflow").

    Returns:
        A list of raw commit objects (dicts) as returned by the GitHub API,
        in the order pages were fetched. Empty list if the first request
        fails or the repo has no commits.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}

    # "Session" object allows us to enable Retries
    session = requests.Session()
    # Retries both connection-level failures (DNS/dropped connections, via
    # `total`) and the transient HTTP statuses in RETRYABLE_STATUS_CODES,
    # with exponential backoff so we don't hammer a rate-limited API.
    retry_strategy = Retry(
        total=MAX_CONNECTION_RETRIES,
        status_forcelist=RETRYABLE_STATUS_CODES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)

    all_commits = []
    page = 1

    # Fetch up to MAX_PAGES pages (approx MAX_PAGES * PER_PAGE commits)
    while page <= MAX_PAGES:
        print(f"Fetching page {page}...")
        params = {'page': page, 'per_page': PER_PAGE}

        try:
            response = session.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raises error for 4xx/5xx codes
            data = response.json()

            if not data:
                break  # Stop if no more data

            all_commits.extend(data)
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break

    return all_commits


def upload_to_s3(data: list[dict], filename: str) -> None:
    """Upload extracted commit data to S3 as a JSON object.

    Args:
        data: List of raw commit objects to serialize and upload.
        filename: Object key suffix; the object is written to
            `raw/<filename>` in AWS_BUCKET.
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    try:
        s3.put_object(
            Bucket=AWS_BUCKET,
            Key=f"raw/{filename}",
            Body=json.dumps(data)
        )
        print(f"Success! Uploaded {filename} to S3.")
    except Exception as e:
        print(f"S3 Upload Failed: {e}")


if __name__ == "__main__":
    commits = get_commits(DEFAULT_REPO_OWNER, DEFAULT_REPO_NAME)
    if commits:
        file_name = f"commits_{datetime.now().strftime('%Y%m%d')}.json"
        upload_to_s3(commits, file_name)