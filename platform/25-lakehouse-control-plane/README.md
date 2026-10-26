# Lakehouse Control Plane

Wave 25. Creates the `lakehouse-control-plane` and `lakehouse-maintenance-operations` namespaces and deploys the table maintenance control plane as the Helm release `table-maintenance` (`chart/`).

## Deployed Resources

```
Namespace: lakehouse-control-plane
  Deployment table-maintenance-db             PostgreSQL 17.11 (PVC, Recreate), Service table-maintenance-db:5432
  Job        table-maintenance-migrate-<rev>  creates the schema, seeds the "default" policy template
  Deployment table-maintenance-api            Service table-maintenance-api:8000
  Deployment table-maintenance-worker         Temporal worker (task queue table-maintenance)
  Deployment table-maintenance-event-consumer Polaris catalog events from Kafka (1 replica)
Namespace: lakehouse-maintenance-operations
  ServiceAccount/Role/RoleBinding table-maintenance-spark   Spark driver
  Role/RoleBinding table-maintenance-worker                 worker may manage SparkApplications
```

## Deploy

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/validate.sh
```

`bootstrap.sh`:

1. creates both namespaces;
2. creates Secret `table-maintenance-db` (random password) only if it is missing;
3. copies the Polaris root credential (`polaris-bootstrap-secret`, as `client_id:client_secret`) into Secret `table-maintenance-polaris-credential`, and the RustFS credentials into Secret `table-maintenance-s3`, in both namespaces;
4. runs `build.sh`, which builds `table-maintenance-backend` and `table-maintenance-spark`, tags them with the short git SHA of the last commit touching their source (`-dirty` when uncommitted) and loads them into minikube;
5. runs `helm upgrade --install table-maintenance ./chart --wait`.

The Spark operator (wave 11) must watch `lakehouse-maintenance-operations` (`spark.jobNamespaces`).

## Ordering

The `migrate` Job is a regular Job named with the Helm release revision, so each upgrade runs it again. A pre-install hook would run before the PostgreSQL Deployment exists. The Job waits for `pg_isready`. The api, worker and event-consumer pods have an init container that waits until the `default` policy template exists, which means the migration finished.

## Configuration

All settings are `GLAC_*` environment variables rendered from `chart/values.yaml` into the ConfigMap `table-maintenance-config` (temporal address, catalog URI and names, S3 endpoint, Kafka, Spark, `GLAC_ADMISSION_LIMIT`, `GLAC_DISCOVERY_INTERVAL_SECONDS`). Secrets come from `table-maintenance-db`, `table-maintenance-polaris-credential` and `table-maintenance-s3`.

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryWorkflow` | schedule `table-discovery:catalog={catalog}` (Temporal appends the firing time); ad hoc `table-discovery:catalog={catalog}[:namespace={namespace}]:trigger=adhoc` | `{catalog}`; ad hoc `{catalog}[.{namespace}] · ad hoc` |
| `TableReconciliationWorkflow` | `table-reconciliation:table-uuid={uuid}` | `{catalog}.{namespace}.{table}` at first start |
| `TableMaintenanceWorkflow` | `table-maintenance:table={catalog}.{namespace}.{table}:run={run_id}` (table name as of the run start; stored on the run as `workflow_id`) | `{catalog}.{namespace}.{table} · {operations}` |
| `TableMaintenanceAdmissionWorkflow` | `table-maintenance-admission` | `global Spark maintenance admission (limit={limit})` |

## Call the API

```
kubectl port-forward service/table-maintenance-api 8000:8000 --namespace lakehouse-control-plane --context retail-lakehouse
curl http://localhost:8000/healthz
curl http://localhost:8000/v1/tables
```

No route needs authentication. The main routes, all under `/v1`:

| Route | Use |
|---|---|
| `GET /policy-templates` | templates; the migration seeds `default` |
| `GET, POST /discovery-rules`, `PATCH, DELETE /discovery-rules/{id}` | rules, first match by `priority` wins; `effect` is `include` or `exclude` |
| `GET, PUT /discovery`, `POST /discovery/scan` | the discovery switch and an on-demand scan |
| `GET /tables?status=active` | managed tables (`active`, `paused`, `excluded`, `dropped`) |
| `PUT /tables/{uuid}/settings` | replace a table's settings; omitted keys take the domain defaults |
| `POST /tables/{uuid}/pause`, `/resume`, `/reset-selection` | operator overrides |
| `POST /tables/include`, `/tables/exclude` | manual include or exclude by name |
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`; runs whole-table, ignores cooldowns |
| `GET /tables/{uuid}/runs`, `GET /runs/{run_id}` | run history with per-operation status and metrics |

Create a rule (the `default` template id comes from `GET /v1/policy-templates`):

```
curl -X POST http://localhost:8000/v1/discovery-rules -H 'Content-Type: application/json' \
  -d '{"priority": 10, "effect": "include", "catalog_pattern": "iceberg",
       "namespace_pattern": "e2e", "table_pattern": "tm_e2e_*", "template_id": "<id>"}'
```

Settings keys, per operation: `rewrite_data_files` (`enabled`, `min_interval_seconds`, `scope` = `partition` or `table`, `target_file_size_bytes`, `min_reducible_files`), `rewrite_manifests` (`enabled`, `min_interval_seconds`, `min_small_manifests`, `small_manifest_bytes`), `expire_snapshots` (`enabled`, `min_interval_seconds`, `older_than_seconds`, `retain_last`), `remove_orphan_files` (`enabled`, `min_interval_seconds`, `older_than_seconds` ≥ 86400), plus `reconcile_interval_seconds` at the top level. Unknown keys return 422.

## End-to-end check

`e2e.sh` is a manual check, not part of `validate.sh`. It takes 20 to 40 minutes, mostly Spark start-up (each operation is its own SparkApplication, which downloads the Iceberg jars from Maven Central, so the cluster needs internet access).

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh
```

It:

1. issues a Trino client certificate for user `tm-e2e` (`task trino:issue-cert`) and port-forwards `service/trino` to `localhost:18445` (`TRINO_PORT`) for each query;
2. creates the rule `include iceberg / e2e / tm_e2e_*` with the `default` template, priority 10 (reused if it exists);
3. creates `iceberg.e2e.tm_e2e_orders` (partitioned by `day(order_ts)`, `bucket(id, 4)`) and `iceberg.e2e.tm_e2e_regions` (partitioned by `region`) if missing, pauses them if they are already registered, inserts 20 and 8 single-row commits, and deletes one order to add a delete file; half of the regions are `o'neil`;
4. waits up to 15 minutes for both tables to be `active`, prints when each `table-reconciliation:table-uuid={uuid}` workflow's current run started next to the discovery schedule's recent runs (on a table's first run, a reconcile start before the next scheduled run means the event path found the table), then pauses both tables and waits for running runs to finish;
5. while paused, lowers the orders thresholds (`min_reducible_files: 2`, `min_small_manifests: 1`, `expire_snapshots.older_than_seconds: 60`, `retain_last: 1`, `remove_orphan_files.older_than_seconds: 86400`) and sets regions to `scope: partition`, `min_reducible_files: 2`, `min_interval_seconds: 60`;
6. resumes orders and triggers all four operations manually, then resumes regions so the scheduled plan compacts through a `where` filter that contains the escaped quote;
7. requires every operation of the new runs to be `succeeded` with `rewritten_data_files_count > 0`, the orders data file count (`$files`) and snapshot count (`$snapshots`) to decrease, `expire_snapshots` to delete files and the RustFS object count under the orders `data/` prefix (one-off `pgsty/mc` pod) to be at most before + files added by the rewrite − files expired (the raw count can grow, because `older_than` is fixed at plan time and the rewrite's partial-progress commits still reference the old files), the regions file count to decrease, the regions `where` filter to contain `'o\'neil'` (read from the history of the run's maintenance workflow, whose ID the API returns as `workflow_id`), and both `table-reconciliation:table-uuid={uuid}` workflows to be running.

If a Spark driver cannot deliver its result callback (the API or its database is down), the polling fallback records the operation as `succeeded` with `{"completed_without_callback": 1}` and no procedure metrics; the check then relies on the `$files` count alone and says so. Only `[INFO]` progress lines are printed; on failure the full output is dumped. The script is idempotent: it reuses the tables and the rule, so a rerun adds new small files. `remove_orphan_files` keeps files younger than one day, so it succeeds without deleting the files just written.

The e2e tables and the rule stay in place to show the scheduled path. To remove them:

```
curl -X DELETE http://localhost:8000/v1/discovery-rules/<rule-id>
trino> DROP TABLE iceberg.e2e.tm_e2e_orders; DROP TABLE iceberg.e2e.tm_e2e_regions; DROP SCHEMA iceberg.e2e;
task trino:delete-cert TRINO_USER=tm-e2e KUBE_CONTEXT=retail-lakehouse
```

Discovery then marks the tables `dropped` and their reconcile workflows end.

## Logs

```
kubectl logs deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse
```
