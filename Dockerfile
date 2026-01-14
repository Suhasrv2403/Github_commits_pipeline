# Start with Airflow
FROM apache/airflow:2.7.1

USER root
# Install git (required for dbt dependencies)
RUN apt-get update && apt-get install -y git && apt-get clean

USER airflow

# Install python libraries
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy your project files
COPY --chown=airflow:root . /opt/airflow/