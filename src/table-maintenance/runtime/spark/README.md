# Table maintenance Spark runtime

Runs the planned Iceberg maintenance of one table operation inside a `SparkApplication` and
reports the result back to the control plane.

## Contract

Environment variables:

| Variable | Meaning |
|---|---|
| `GLAC_REQUEST` | JSON of the submit gateway input: `app_name`, `run_id`, `operation`, `attempt`, `catalog`, `namespace`, `table`, `where` (list of filters), `procedure_args`, `callback_url` |
| `POLARIS_CREDENTIAL` | Polaris client credential, injected from a Secret; set as `spark.sql.catalog.{catalog}.credential` when present |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | S3 access for the Iceberg `S3FileIO` |

The runtime runs one `CALL \`{catalog}\`.system.{operation}(...)` per entry of `where`
(`where => '<filter>'`), or a single whole-table CALL when `where` is empty. Operations are
`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots` and `remove_orphan_files`; any
other value fails the job. String arguments are embedded with Spark escaping (backslash
doubled, then quote backslash-escaped). The session time zone is UTC.

Integer result columns are summed by name across the CALLs and reported as `metrics`.

## Callback

After the CALLs finish, the runtime POSTs JSON to `callback_url` (3 tries, 5 s apart):

```json
{"run_id": "...", "operation": "...", "attempt": 1, "succeeded": true,
 "metrics": {"rewritten_data_files_count": 5}, "error": null}
```

The exit code is 0 on success and 1 on failure, independent of callback delivery. If the
callback never arrives, the workflow falls back to polling the SparkApplication state.

## Tests

```
uv run --project src/table-maintenance/runtime/spark --directory src/table-maintenance/runtime/spark pytest -q
```

Spark is mocked; no JVM is started.
