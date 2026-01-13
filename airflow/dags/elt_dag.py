from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

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

    # Task 1: Run the Extract Script (Python)
    # We explicitly load the .env file before running the script
    t1 = BashOperator(
        task_id='extract_github_data',
        bash_command='cd /opt/airflow && export $(cat .env | xargs) && python src/extract.py',
    )

    # Task 2: Run dbt (Transformation)
    # We point to the dbt project folder mounted in the container
    t2 = BashOperator(
        task_id='dbt_transform',
        bash_command='cd /opt/airflow/dbt && dbt run --profiles-dir /opt/airflow/.dbt',
    )

    # Task 3: Run dbt tests (Data Quality)
    t3 = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt && dbt test --profiles-dir /opt/airflow/.dbt',
    )

    # Define the dependency chain
    t1 >> t2 >> t3