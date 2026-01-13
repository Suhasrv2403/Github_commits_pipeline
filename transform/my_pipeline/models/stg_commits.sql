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