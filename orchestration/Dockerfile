FROM apache/airflow:2.7.1

# Switch to root to install git (needed for dbt)
USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean

# Switch back to airflow user to install Python libs
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt