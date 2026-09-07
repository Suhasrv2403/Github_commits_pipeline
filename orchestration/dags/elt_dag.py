"""Airflow DAG for the GitHub-to-Snowflake ELT pipeline.

Defines the `elt_pipeline` DAG, which runs daily and chains four
BashOperator tasks against the project's Python/dbt code (mounted into
the Airflow container, see orchestration/docker-compose.yaml):

    extract_github_data -> load_to_snowflake -> dbt_transform -> dbt_test

1. extract_github_data: runs scripts/run_extract.py (which calls into
   src/extract.py's library functions) to pull commits from the GitHub
   API and land them in S3.
2. load_to_snowflake: runs the load_raw_commits dbt macro (see
   transform/my_pipeline/macros/load_raw_commits.sql) to COPY INTO the
   raw JSON just landed in S3 into Snowflake's github_raw.RAW_COMMITS,
   which dbt_transform's models read from. Requires the stage/table set
   up once via transform/my_pipeline/analyses/setup_raw_ingestion.sql.
3. dbt_transform: runs `dbt run` against transform/my_pipeline to build
   the staging/fact models from the raw data just loaded into Snowflake.
4. dbt_test: runs `dbt test` to validate the resulting models
   (see transform/my_pipeline/models/schema.yml).

Secrets (GitHub/AWS/Snowflake credentials) are not set as Airflow
Variables/Connections; they are read from a mounted `.env` file and
merged into each task's shell environment.

Non-secret scheduling settings (schedule interval, retries, start date)
are read from the `orchestration:` section of configs/config.yml at the
repo root (mounted into the container, see orchestration/docker-compose.yaml),
falling back to the defaults below if that file or key is absent.
"""
from datetime import datetime, timedelta
from typing import Any
from airflow import DAG
from airflow.operators.bash import BashOperator
from dotenv import dotenv_values
import os
import yaml

# 1. Load the secrets
config: dict[str, str | None] = dotenv_values("/opt/airflow/.env")

# 2. LOAD SYSTEM DEFAULTS (Critical Fix!) 🛠️
# Start with the existing system environment (which contains the PATH to dbt)
env_config: dict[str, str] = os.environ.copy()

# 3. Merge your secrets into the system environment
env_config.update(config)

# 4. Load non-secret scheduling config, falling back to these defaults
# (which match what used to be hardcoded here) if config.yml is missing.
_ORCHESTRATION_CONFIG_DEFAULTS: dict[str, Any] = {
    'schedule_interval': '@daily',
    'retries': 1,
    'retry_delay_minutes': 5,
    'start_date': '2024-01-01',
}
try:
    with open('/opt/airflow/configs/config.yml') as f:
        _file_config = (yaml.safe_load(f) or {}).get('orchestration', {}) or {}
except FileNotFoundError:
    _file_config = {}
orchestration_config: dict[str, Any] = {**_ORCHESTRATION_CONFIG_DEFAULTS, **_file_config}

default_args: dict[str, Any] = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': orchestration_config['retries'],
    'retry_delay': timedelta(minutes=orchestration_config['retry_delay_minutes']),
}

with DAG(
    'elt_pipeline',
    default_args=default_args,
    description='A simple ELT pipeline for GitHub Data',
    schedule_interval=orchestration_config['schedule_interval'],
    start_date=datetime.strptime(orchestration_config['start_date'], '%Y-%m-%d'),
    catchup=False,
) as dag:

    # Task 1: Extract
    t1 = BashOperator(
        task_id='extract_github_data',
        bash_command='cd /opt/airflow && python scripts/run_extract.py',
        env=env_config,  # Now includes PATH + Secrets
    )

    # Task 2: Load raw JSON from S3 into Snowflake (github_raw.RAW_COMMITS)
    t2 = BashOperator(
        task_id='load_to_snowflake',
        bash_command='cd /opt/airflow/dbt && dbt run-operation load_raw_commits --profiles-dir .',
        env=env_config,
    )

    # Task 3: dbt Run
    t3 = BashOperator(
        task_id='dbt_transform',
        bash_command='cd /opt/airflow/dbt && dbt run --profiles-dir .',
        env=env_config,
    )

    # Task 4: dbt Test
    t4 = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt && dbt test --profiles-dir .',
        env=env_config,
    )

    t1 >> t2 >> t3 >> t4