-- Fact model: one row per commit, materialized as a table for downstream
-- reporting/BI. Input: stg_commits (see stg_commits.sql). Output adds
-- commit_date (a plain DATE) alongside the staged columns for daily rollups.
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