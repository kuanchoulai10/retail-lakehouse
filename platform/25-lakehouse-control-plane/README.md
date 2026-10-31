# Lakehouse Control Plane

Wave 25. Creates the `lakehouse-control-plane` and `lakehouse-maintenance-operations` namespaces and deploys the table maintenance control plane as the Helm release `table-maintenance` (`chart/`).

## Deployed Resources

```
Namespace: lakehouse-control-plane
  Deployment table-maintenance-db             PostgreSQL 17.11 (PVC, Recreate), Service table-maintenance-db:5432
  Job        table-maintenance-migrate-<rev>  creates the schema, seeds the "default" table maintenance preset
  Deployment table-maintenance-api            Service table-maintenance-api:8000
  Deployment table-maintenance-worker         Temporal worker (task queue table-maintenance)
  Deployment table-maintenance-event-consumer Polaris catalog events from Kafka (1 replica)
  Deployment console                          data platform console (nginx), Service console:8080
  HTTPRoute  console                          PathPrefix /console on platform-gateway (istio-ingress)
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
4. runs `build.sh`, which builds `table-maintenance-backend`, `table-maintenance-spark` and `console` (`src/console`), tags them with the short git SHA of the last commit touching their source (`-dirty` when uncommitted) and loads them into minikube;
5. runs `helm upgrade --install table-maintenance ./chart --wait`.

The Spark operator (wave 11) must watch `lakehouse-maintenance-operations` (`spark.jobNamespaces`).

## Console

The console is a static app served by nginx at `/console/`; nginx proxies `/console/api/` to `table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`, so the browser talks to one origin. nginx resolves that name at start-up, which works because the api Service is in the same release. The `console` HTTPRoute attaches to `platform-gateway` (wave 22), whose `allowedRoutes` admits `lakehouse-catalog` and `lakehouse-control-plane`; `PathPrefix /console` is more specific than the Polaris catch-all on `/`.

```
kubectl port-forward service/platform-gateway-istio 8080:80 --namespace istio-ingress --context retail-lakehouse
open http://localhost:8080/console/
```

`validate.sh` waits for the `console` rollout and the route's `Accepted` condition, then port-forwards the gateway to `localhost:18080` (`GATEWAY_PORT`) and checks that `/console/` and the deep link `/console/tables/x/commits` return the app and `/console/api/v1/tables` returns a JSON array.

## Ordering

The `migrate` Job is a regular Job named with the Helm release revision, so each upgrade runs it again. A pre-install hook would run before the PostgreSQL Deployment exists. The Job waits for `pg_isready`. The api, worker and event-consumer pods have an init container that waits until the `default` preset exists, which means the migration finished.

## Configuration

All settings are `GLAC_*` environment variables rendered from `chart/values.yaml` into the ConfigMap `table-maintenance-config` (temporal address, catalog URI and names, S3 endpoint, Kafka, Spark, `GLAC_ADMISSION_LIMIT`, `GLAC_DISCOVERY_INTERVAL_SECONDS`). Secrets come from `table-maintenance-db`, `table-maintenance-polaris-credential` and `table-maintenance-s3`.

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryWorkflow` | schedule `table-discovery:catalog={catalog}` (Temporal appends the firing time); ad hoc `table-discovery:catalog={catalog}[:namespace={namespace}]:trigger=adhoc` | `{catalog}`; ad hoc `{catalog}[.{namespace}] · ad hoc` |
| `TableReconciliationWorkflow` | `table-reconciliation:table-uuid={uuid}` | `{catalog}.{namespace}.{table}` at first start |
| `TableMaintenanceWorkflow` | `table-maintenance:table={catalog}.{namespace}.{table}:run={run_id}` (table name as of the run start; stored on the run as `execution_ref`) | `{catalog}.{namespace}.{table} · {operations}` |
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
| `GET, POST /table-maintenance-presets`, `GET, PATCH, DELETE /table-maintenance-presets/{preset_id}` | presets; the migration seeds `default` |
| `GET, POST /table-discovery-rules`, `PATCH, DELETE /table-discovery-rules/{rule_id}` | rules, first match by `priority` wins; `effect` is `include` or `exclude` |
| `GET, PUT /table-discovery-settings`, `POST /table-discovery-settings/scan` | the discovery switch and an on-demand scan |
| `GET /tables?status=active` | tables (formerly managed tables; `active`, `paused`, `excluded`, `dropped`) |
| `PUT /tables/{uuid}/settings` | replace a table's settings; omitted keys take the domain defaults |
| `POST /tables/{uuid}/pause`, `/resume`, `/reset-selection` | operator overrides |
| `POST /tables/include`, `/tables/exclude` | manual include or exclude by name |
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`; runs whole-table, ignores cooldowns |
| `GET /tables/{uuid}/table-maintenance-runs`, `GET /table-maintenance-runs/{run_id}` | run history with per-operation status and metrics |

Create a rule (the `default` preset id comes from `GET /v1/table-maintenance-presets`):

```
curl -X POST http://localhost:8000/v1/table-discovery-rules -H 'Content-Type: application/json' \
  -d '{"priority": 10, "effect": "include", "catalog_pattern": "iceberg",
       "namespace_pattern": "e2e", "table_pattern": "tm_e2e_*", "preset_id": "<id>"}'
```

Settings keys, per operation: `rewrite_data_files` (`enabled`, `min_interval_seconds`, `scope` = `partition` or `table`, `target_file_size_bytes`, `min_reducible_files`), `rewrite_manifests` (`enabled`, `min_interval_seconds`, `min_small_manifests`, `small_manifest_bytes`), `expire_snapshots` (`enabled`, `min_interval_seconds`, `older_than_seconds`, `retain_last`), `remove_orphan_files` (`enabled`, `min_interval_seconds`, `older_than_seconds` ≥ 86400), plus `reconcile_interval_seconds` at the top level. Unknown keys return 422.

## End-to-end check

`e2e.sh` is a manual check, not part of `validate.sh`. It takes 20 to 40 minutes, mostly Spark start-up (each operation is its own SparkApplication, which downloads the Iceberg jars from Maven Central, so the cluster needs internet access).

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh
```

It:

1. issues a Trino client certificate for user `tm-e2e` (`task trino:issue-cert`) and port-forwards `service/trino` to `localhost:18445` (`TRINO_PORT`) for each query;
2. creates the rule `include iceberg / e2e / tm_e2e_*` with the `default` preset, priority 10 (reused if it exists);
3. creates `iceberg.e2e.tm_e2e_orders` (partitioned by `day(order_ts)`, `bucket(id, 4)`) and `iceberg.e2e.tm_e2e_regions` (partitioned by `region`) if missing, pauses them if they are already registered, inserts 20 and 8 single-row commits, and deletes one order to add a delete file; half of the regions are `o'neil`;
4. waits up to 15 minutes for both tables to be `active`, prints when each `table-reconciliation:table-uuid={uuid}` workflow's current run started next to the discovery schedule's recent runs (on a table's first run, a reconcile start before the next scheduled run means the event path found the table), then pauses both tables and waits for running runs to finish;
5. while paused, lowers the orders thresholds (`min_reducible_files: 2`, `min_small_manifests: 1`, `expire_snapshots.older_than_seconds: 60`, `retain_last: 1`, `remove_orphan_files.older_than_seconds: 86400`) and sets regions to `scope: partition`, `min_reducible_files: 2`, `min_interval_seconds: 60`;
6. resumes orders and triggers all four operations manually, then resumes regions so the scheduled plan compacts through a `where` filter that contains the escaped quote;
7. requires every operation of the new runs to be `succeeded` with `rewritten_data_files_count > 0`, the orders data file count (`$files`) and snapshot count (`$snapshots`) to decrease, `expire_snapshots` to delete files and the RustFS object count under the orders `data/` prefix (one-off `pgsty/mc` pod) to be at most before + files added by the rewrite − files expired (the raw count can grow, because `older_than` is fixed at plan time and the rewrite's partial-progress commits still reference the old files), the regions file count to decrease, the regions `where` filter to contain `'o\'neil'` (read from the history of the run's maintenance workflow, whose ID the API returns as `execution_ref`), and both `table-reconciliation:table-uuid={uuid}` workflows to be running;
8. reads the orders `metadata`, `commits?limit=1000`, `health` and `storage` through the API and requires `total_data_files + total_delete_files` to equal the `$files` count (Trino's `$files` lists data and delete files), `snapshot_count` to equal the `$snapshots` count, the commits to be newest first, `health` to report four operations and `storage.reclaimed.rewritten_data_files` to be at least 20 (skipped when the compaction callback was lost).

If a Spark driver cannot deliver its result callback (the API or its database is down), the polling fallback records the operation as `succeeded` with `{"completed_without_callback": 1}` and no procedure metrics; the check then relies on the `$files` count alone and says so. Only `[INFO]` progress lines are printed; on failure the full output is dumped. The script is idempotent: it reuses the tables and the rule, so a rerun adds new small files. `remove_orphan_files` keeps files younger than one day, so it succeeds without deleting the files just written.

The e2e tables and the rule stay in place to show the scheduled path. To remove them:

```
curl -X DELETE http://localhost:8000/v1/table-discovery-rules/<rule-id>
trino> DROP TABLE iceberg.e2e.tm_e2e_orders; DROP TABLE iceberg.e2e.tm_e2e_regions; DROP SCHEMA iceberg.e2e;
task trino:delete-cert TRINO_USER=tm-e2e KUBE_CONTEXT=retail-lakehouse
```

Discovery then marks the tables `dropped` and their reconcile workflows end.

## Logs

```
kubectl logs deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse
```
