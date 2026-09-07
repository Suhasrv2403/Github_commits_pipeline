"""CLI entry point for the extract step: pull commits, upload to S3.

Thin wrapper around the reusable get_commits/upload_to_s3 functions in
src/extract.py (core library code lives there; this script is just the
`__main__` trigger). Invoked directly — `python scripts/run_extract.py` —
by the extract_github_data task in orchestration/dags/elt_dag.py.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extract import DEFAULT_REPO_OWNER, DEFAULT_REPO_NAME, get_commits, upload_to_s3  # noqa: E402

if __name__ == "__main__":
    commits = get_commits(DEFAULT_REPO_OWNER, DEFAULT_REPO_NAME)
    if commits:
        file_name = f"commits_{datetime.now().strftime('%Y%m%d')}.json"
        upload_to_s3(commits, file_name)
