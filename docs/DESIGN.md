# Design Notes

Deeper technical detail than belongs in the top-level README: the DAG
task-by-task, the dbt lineage and why the load step is shaped the way it
is, the security/reproducibility decisions, known limitations, and
references.

## Pipeline, task by task

The `elt_pipeline` Airflow DAG (`orchestration/dags/elt_dag.py`) runs daily
and chains four `BashOperator` tasks:

```
extract_github_data -> load_to_snowflake -> dbt_transform -> dbt_test
```

1. **extract_github_data** — runs `scripts/run_extract.py`, which calls
   `src/extract.py`'s `get_commits()` to page through the GitHub REST API
   (up to `configs/config.yml`'s `max_pages` pages of `per_page` commits
   each) and `upload_to_s3()` to write the raw JSON array to
   `s3://$AWS_BUCKET/raw/commits_<YYYYMMDD>.json`.
2. **load_to_snowflake** — runs the `load_raw_commits` dbt macro
   (`transform/my_pipeline/macros/load_raw_commits.sql`), which `COPY
   INTO`s that S3 object into Snowflake's `github_raw.RAW_COMMITS` table
   using `STRIP_OUTER_ARRAY = TRUE` — this unpacks the single JSON array
   extract.py uploads into one `VARIANT` row per commit, which is the
   shape `stg_commits.sql` expects. This is the load step that connects
   extraction to transformation; before it existed, `stg_commits.sql` had
   no actual data feeding it. The one-time DDL for the destination table
   and S3 stage lives in `transform/my_pipeline/analyses/setup_raw_ingestion.sql`
   (a dbt "analysis" — compiled but never auto-run) and must be applied
   manually once per Snowflake account.
3. **dbt_transform** (`dbt run`) — builds `stg_commits` (parses
   `raw_data:sha`, `raw_data:commit:author:name/date`, etc. into typed
   columns) and `fact_commits` (adds a derived `commit_date`, materialized
   as a table).
4. **dbt_test** (`dbt test`) — runs the `unique`/`not_null` tests declared
   in `transform/my_pipeline/models/schema.yml` against both models.

## Reproducibility

- **No RNG-based nondeterminism exists in this codebase** (confirmed by
  grepping for `random`/`numpy.random`/shuffle/sample — none found). The
  only run-to-run variation is intentional wall-clock timestamping (the
  extract output filename, the load macro's `ingested_at`), which is
  supposed to differ per run.
- Every non-secret, tunable value (GitHub repo, pagination, retry
  policy, DAG schedule) lives in `configs/config.yml`, with a code-level
  default matching prior hardcoded behavior so every script still runs
  correctly with zero setup if that file is missing.
- Secrets never go in config — they're read from a local `.env` (see
  `.env.example`), which is gitignored.

## Security decisions

- Airflow's Fernet key (encrypts Connection passwords at rest) and the
  local admin login were previously static values committed to version
  control. Both now come from `.env`, and the compose file fails loudly
  (`${VAR:?message}`) rather than silently falling back to an insecure
  default, for the two sensitive ones.
- The one-time Snowflake setup script uses a **Storage Integration**
  rather than embedding AWS keys in `CREATE STAGE ... CREDENTIALS = (...)`
  SQL, so no AWS secret ever needs to exist in SQL text or a Snowflake
  query history.

## Retry/backoff policy

`get_commits()` retries on `429` (explicit rate limit) and `5xx`
(transient server errors) with exponential backoff, but **deliberately
excludes GitHub's `403`**: GitHub overloads that status for both
rate-limiting and genuine auth/permission failures (e.g. a revoked
token), and retrying a broken token would just waste time without ever
succeeding.

## Known limitations

- **Fixed page cap.** `max_pages` (default 5, ~150 commits) is not
  cursor-based — a repo with more daily commits than that will silently
  lose the overflow. Fixing this properly means paginating off the
  `Link` response header (or switching to the GraphQL API) instead of a
  fixed count.
- **No dedup/incremental load.** `fact_commits` is a full-table rebuild
  (`materialized: table`) on every `dbt run`; there's no logic to skip
  or merge commits already loaded if the DAG reruns the same day.
- **Minimal test coverage on the warehouse side.** dbt tests are just
  `unique`/`not_null` on the two models — no referential integrity,
  freshness, or row-count anomaly checks.
- **Single hardcoded default repo.** `scripts/run_extract.py` takes no
  CLI arguments; which repo to extract is set via `configs/config.yml`
  (`extract.repo_owner`/`repo_name`), not passed per-invocation.
- **Local-dev-only Postgres credentials.** The Airflow metadata
  database's `airflow:airflow` credentials in `orchestration/docker-compose.yaml`
  are still static (unlike the Fernet key/admin login, which are now
  sourced from `.env`). This is standard for a Postgres container that
  never leaves the local Docker network, but it's not something to carry
  into a shared environment.
- **No monitoring/alerting.** A failed DAG run is only visible in the
  Airflow UI; there are no SLAs, alerts, or dbt source-freshness checks.
- **`ON_ERROR = 'continue'` on the COPY INTO** means a malformed record
  is silently skipped rather than quarantined — fine for a portfolio
  project, not for a pipeline anyone depends on for complete data.

## References

- [GitHub REST API — List commits](https://docs.github.com/en/rest/commits/commits#list-commits)
- [dbt docs](https://docs.getdbt.com/)
- [Apache Airflow docs](https://airflow.apache.org/docs/)
- [Snowflake `COPY INTO` (JSON, `STRIP_OUTER_ARRAY`)](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)
- [Snowflake Storage Integrations](https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration)
