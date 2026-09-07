{% macro load_raw_commits() %}
    {#
        Loads newly-landed raw commit JSON from the S3 bucket that
        src/extract.py writes to (s3://$AWS_BUCKET/raw/) into the
        github_raw.RAW_COMMITS table declared in models/sources.yml, which
        models/stg_commits.sql reads from.

        This is the load step of the ELT pipeline; previously nothing in
        the repo connected the extract step's S3 output to the dbt models'
        expected Snowflake input. STRIP_OUTER_ARRAY unpacks the single JSON
        array extract.py uploads per run into one VARIANT row per commit,
        matching the one-commit-per-row shape stg_commits.sql expects.

        Prerequisite (one-time, outside dbt): the destination table and an
        external stage over the S3 bucket must already exist — see
        analyses/setup_raw_ingestion.sql.

        Invoked via `dbt run-operation load_raw_commits`; wired into
        orchestration/dags/elt_dag.py as the load_to_snowflake task, between
        extract_github_data and dbt_transform.
    #}
    {% set raw_table = source('github_raw', 'RAW_COMMITS') %}
    {% set stage_ref = raw_table.database ~ '.' ~ raw_table.schema ~ '.github_commits_stage' %}

    {% set load_sql %}
        copy into {{ raw_table }} (raw_data, ingested_at)
        from (
            select $1, current_timestamp()
            from @{{ stage_ref }}
        )
        file_format = (type = json, strip_outer_array = true)
        on_error = 'continue'
    {% endset %}

    {% do log("Loading raw GitHub commit JSON into " ~ raw_table, info=true) %}
    {% do run_query(load_sql) %}
{% endmacro %}
