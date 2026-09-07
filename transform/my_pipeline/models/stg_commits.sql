-- Staging model: cleans/casts the raw GitHub commit JSON landed in Snowflake
-- (via S3 + an external COPY INTO, see sources.yml for github_raw.RAW_COMMITS)
-- into typed columns. Consumed by fact_commits.sql.
-- Input:  github_raw.RAW_COMMITS (raw_data VARIANT, ingested_at TIMESTAMP)
-- Output: one row per commit with commit_hash, author_name, commit_at,
--         commit_message, commit_url, ingested_at
WITH raw_source AS (
    SELECT * FROM {{ source('github_raw', 'RAW_COMMITS') }}
),

parsed_data AS (
    SELECT
        -- Parse the JSON (Snowflake syntax)
        raw_data:sha::STRING as commit_hash,
        raw_data:commit:author:name::STRING as author_name,
        raw_data:commit:author:date::TIMESTAMP as commit_at,
        raw_data:commit:message::STRING as commit_message,
        raw_data:html_url::STRING as commit_url,
        ingested_at
    FROM raw_source
)

SELECT * FROM parsed_data