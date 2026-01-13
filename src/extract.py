import os
import requests
import json
import boto3
from datetime import datetime

# Load secrets from Environment Variables (Docker will provide these)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
AWS_BUCKET = os.getenv('AWS_BUCKET')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')


def get_commits(repo_owner, repo_name):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}

    # "Session" object allows us to enable Retries
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('https://', adapter)

    all_commits = []
    page = 1

    # Fetch 5 pages (approx 150 commits)
    while page <= 5:
        print(f"Fetching page {page}...")
        params = {'page': page, 'per_page': 30}

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


def upload_to_s3(data, filename):
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
    commits = get_commits('apache', 'airflow')
    if commits:
        file_name = f"commits_{datetime.now().strftime('%Y%m%d')}.json"
        upload_to_s3(commits, file_name)