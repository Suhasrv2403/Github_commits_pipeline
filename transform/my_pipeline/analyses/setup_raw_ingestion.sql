-- One-time Snowflake setup for the raw GitHub commit ingestion path.
-- This is a dbt "analysis": dbt will compile it (rendering the source()
-- reference below to a real database.schema.table path you can copy out),
-- but never runs or materializes it. Run it manually, once, as a role
-- with CREATE STAGE / CREATE TABLE privileges on the target database/schema.
--
-- Without this, macros/load_raw_commits.sql has nothing to load from —
-- the stage and table it references must already exist.
--
-- Prerequisite: a Snowflake STORAGE INTEGRATION over the S3 bucket that
-- src/extract.py writes to (AWS_BUCKET in .env.example), created once by
-- ACCOUNTADMIN so no AWS keys ever need to be embedded in SQL:
--
--   CREATE STORAGE INTEGRATION github_commits_s3_int
--     TYPE = EXTERNAL_STAGE
--     STORAGE_PROVIDER = 'S3'
--     ENABLED = TRUE
--     STORAGE_AWS_ROLE_ARN = '<iam-role-arn-with-read-access-to-the-bucket>'
--     STORAGE_ALLOWED_LOCATIONS = ('s3://<AWS_BUCKET>/raw/');
--
--   -- then grant usage on it to the role dbt/Airflow connects as:
--   GRANT USAGE ON INTEGRATION github_commits_s3_int TO ROLE <your_role>;

create table if not exists {{ source('github_raw', 'RAW_COMMITS') }} (
    raw_data variant,
    ingested_at timestamp_ntz
);

create stage if not exists {{ source('github_raw', 'RAW_COMMITS').database }}.{{ source('github_raw', 'RAW_COMMITS').schema }}.github_commits_stage
    url = 's3://<AWS_BUCKET>/raw/'
    storage_integration = github_commits_s3_int;
