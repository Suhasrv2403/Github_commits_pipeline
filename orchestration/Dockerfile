# Canonical Airflow image for this project — built by orchestration/docker-compose.yaml
# (`build: .` resolves relative to this file's directory). A near-duplicate
# used to also exist at the repo root; it was unreferenced by anything and
# has been removed. This image intentionally does NOT COPY the project's
# code in (no `COPY . /opt/airflow/`): docker-compose bind-mounts
# dags/src/transform live instead, so local edits take effect without a
# rebuild. If this image is ever run standalone (no compose, no volumes —
# e.g. a managed Airflow deployment), add a `COPY --chown=airflow:root . /opt/airflow/`
# step back in to bake the code into the image.
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