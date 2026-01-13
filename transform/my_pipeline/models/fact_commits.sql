{{ config(
    materialized='table'
) }}

SELECT
    commit_hash,
    author_name,
    commit_message,
    commit_at,
    commit_url,
    -- Simple transformation: extract just the date for daily reporting
    TO_DATE(commit_at) as commit_date
FROM {{ ref('stg_commits') }}
-- We use ref() so dbt knows to run stg_commits first!