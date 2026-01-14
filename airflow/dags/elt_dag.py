from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from dotenv import dotenv_values
import os

# 1. Load the secrets
config = dotenv_values("/opt/airflow/.env")

# 2. LOAD SYSTEM DEFAULTS (Critical Fix!) 🛠️
# Start with the existing system environment (which contains the PATH to dbt)
env_config = os.environ.copy()

# 3. Merge your secrets into the system environment
env_config.update(config)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'elt_pipeline',
    default_args=default_args,
    description='A simple ELT pipeline for GitHub Data',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    # Task 1: Extract
    t1 = BashOperator(
        task_id='extract_github_data',
        bash_command='cd /opt/airflow && python src/extract.py',
        env=env_config,  # Now includes PATH + Secrets
    )

    # Task 2: dbt Run
    t2 = BashOperator(
        task_id='dbt_transform',
        bash_command='cd /opt/airflow/transform/my_pipeline && dbt run --profiles-dir .',
        env=env_config,
    )

    # Task 3: dbt Test
    t3 = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/transform/my_pipeline && dbt test --profiles-dir .',
        env=env_config,
    )

    t1 >> t2 >> t3