# Lakehouse Control Plane

Wave 25. Creates the `lakehouse-control-plane` and `lakehouse-maintenance-operations` namespaces and deploys the table maintenance control plane as the Helm release `table-maintenance` (`chart/`).

## Deployed Resources

```
Namespace: lakehouse-control-plane
  Deployment table-maintenance-db             PostgreSQL 17.11 (PVC, Recreate), Service table-maintenance-db:5432
  Job        table-maintenance-migrate-<rev>  creates the schema, seeds the "default" maintenance policy
  Deployment table-maintenance-api            Service table-maintenance-api:8000
  Deployment table-maintenance-worker         Temporal worker (task queue table-maintenance)
  Deployment table-maintenance-event-consumer Polaris catalog events from Kafka (1 replica)
  Deployment console                          data platform console (nginx), Service console:8080
  HTTPRoute  console                          /console on platform-gateway (istio-ingress)
Namespace: lakehouse-maintenance-operations
  ServiceAccount/Role/RoleBinding table-maintenance-spark   Spark driver
  Role/RoleBinding table-maintenance-worker                 worker may manage SparkApplications
Cluster-scoped
  Queue (volcano)  table-maintenance, table-maintenance-urgent   capability cpu 2 / memory 5017Mi (one L job) each
  PriorityClass    table-maintenance-p0 .. p3                    values 1000003 .. 1000000, preemptionPolicy Never
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
4. runs `build.sh`, which builds `table-maintenance-backend`, `table-maintenance-spark` and `console` (`src/data-platform/frontend`), tags them with the short git SHA of the last commit touching their source (`-dirty` when uncommitted) and loads them into minikube;
5. runs `helm upgrade --install table-maintenance ./chart --wait`.

The Spark operator (wave 11) must watch `lakehouse-maintenance-operations` (`spark.jobNamespaces`).

## Console

The console is a static app served by nginx at `/console/`; nginx proxies `/console/api/` to `table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`, so the browser talks to one origin. nginx resolves that name at start-up, which works because the api Service is in the same release. The `console` HTTPRoute attaches to `platform-gateway` (wave `12-platform-gateway`) with path prefix `/console`; `bootstrap.sh` labels `lakehouse-control-plane` with `gateway::allow_routes` so the Gateway admits it. nginx redirects `/console` to `/console/` with a relative `Location` (`absolute_redirect off`), so the redirect keeps whatever scheme and port the browser used.

```
kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse
open http://localhost:8591/console/
```

`validate.sh` waits for the `console` rollout and the route's `Accepted` condition, then curls the gateway (`gateway::curl`) and checks that `/console`, `/console/` and the deep link `/console/tables/x/commits` return the app and `/console/api/v1/tables` returns a JSON array.

## Ordering

The `migrate` Job is a regular Job named with the Helm release revision, so each upgrade runs it again. A pre-install hook would run before the PostgreSQL Deployment exists. The Job waits for `pg_isready`. The api, worker and event-consumer pods have an init container that waits until the `default` maintenance policy exists, which means the migration finished.

## Configuration

All settings are `GLAC_*` environment variables rendered from `chart/values.yaml` into the ConfigMap `table-maintenance-config` (temporal address, catalog URI and names, S3 endpoint, Kafka, Spark, `GLAC_DISCOVERY_INTERVAL_SECONDS`, `GLAC_MAINTENANCE_*`). Secrets come from `table-maintenance-db`, `table-maintenance-polaris-credential` and `table-maintenance-s3`.

### Spark sizes

Every maintenance attempt runs at one of three sizes, set under `spark.sizes` in `chart/values.yaml` and rendered as `GLAC_SPARK__SIZE_<S|M|L>__DRIVER_MEMORY`, `__EXECUTOR_MEMORY` and `__EXECUTOR_INSTANCES`. Driver and executor stay capped at one core; memory overhead is Spark's default (`max(384Mi, 0.4 × memory)` for a Python application), so the pod requests are:

| Size | Driver memory | Executor memory | Executors | Pod requests, driver + executor |
|---|---|---|---|---|
| S | `768m` | `768m` | 1 | 1152Mi + 1152Mi = 2304Mi |
| M | `1g` | `1536m` | 1 | 1434Mi + 2150Mi = 3584Mi |
| L | `1536m` | `2g` | 1 | 2150Mi + 2867Mi = 5017Mi |

An L job fits on the 8-CPU / 26 GB node only alone; next to another Spark job it stays queued while its queue-wait clock runs (its attempt deadline starts only once its driver runs). A partial override (one `GLAC_SPARK__SIZE_L__EXECUTOR_MEMORY`) keeps the other values of that size.

An operation starts at the size its table last succeeded at (S for a table that never did). Each failed attempt is classified when it is recorded: `oom` (a driver or executor container `OOMKilled` or exit 137, an executor exit 52, or `java.lang.OutOfMemoryError` / `OOMKilled` / `exit code 52` in the error or a driver termination message; container exits count only when Spark itself ended the attempt, since the platform's own deletes also exit 137), `timeout`, `queue_timeout`, `commit_conflict`, `permanent` (missing table, forbidden), `cancelled` or `other`. An attempt's deadline and queue wait are timed apart (see Queue wait and run time); one stopped in the queue is not retried. An `oom` retries at the next size; `permanent` is not retried; other failures retry at the same size, within `worker.maxAttempts` (3) attempts. An `oom` at L stops the operation and marks it **needs attention** on the table: reconcile stops planning it until a manual run of it, or until another policy (or policy version, or the same policy attached elsewhere) applies to the table than the one its run was planned under. The next reconcile after such a change clears the mark for good, so going back to the earlier policy does not bring the block back; until that reconcile, the table API still shows the mark. A success records the attempt's size, and the Spark runtime reports the peak heap the driver and the busiest executor used, in bytes (`peak_driver_heap_bytes`, `peak_executor_heap_bytes`, read from the driver's own Spark UI REST API on localhost before the session stops). A success counts toward stepping down only when both peaks fit within 70% of the next smaller size's driver and executor memory (as set in `spark.sizes`); three such successes in a row at the remembered size step it down one size, and a role with no measured peak never counts. The run API lists every attempt with its size, failure class, event-log state and next step, and the console's Maintenance tab shows them.

### Volcano queues and priorities

Maintenance SparkApplications are scheduled by Volcano. The `volcano` block in `chart/values.yaml` creates two Volcano queues and four PriorityClasses (`chart/templates/volcano.yaml`, wave 10 installs the CRDs) and renders their names for the worker as `GLAC_SPARK__VOLCANO__QUEUE`, `GLAC_SPARK__VOLCANO__URGENT_QUEUE` and `GLAC_SPARK__VOLCANO__PRIORITY_CLASS_PREFIX`:

| Table priority | Queue | PriorityClass | Value |
|---|---|---|---|
| P0 | `table-maintenance-urgent` | `table-maintenance-p0` | 1000003 |
| P1 | `table-maintenance` | `table-maintenance-p1` | 1000002 |
| P2 | `table-maintenance` | `table-maintenance-p2` | 1000001 |
| P3 (default) | `table-maintenance` | `table-maintenance-p3` | 1000000 |

Each queue's `capability` is one L job (`cpu: "2"`, `memory: 5017Mi`), with no `guarantee` and no `reclaimable`. Every size requests 2 CPU and the cap is cpu 2, so each queue runs one job of any size at a time; the cpu cap is what to raise for more concurrency (the memory cap then decides how many fit). Every class has `preemptionPolicy: Never` and `globalDefault: false`: a higher priority is picked first when capacity frees up, but never evicts a running job. The backend sets the class on the PodGroup only, not on the driver and executor pods: the class orders the queue, and pods without one are evicted under node memory pressure no later than platform services, which have none either.

### Queue wait and run time

A maintenance attempt spends its time in two places, waiting in its Volcano queue and then running, and the two are timed apart so a long queue never makes a healthy job time out. An attempt is `queued` from its submit until its Spark driver container starts, which the worker reads from the driver pod on each status poll (`state.running.startedAt`, else `state.terminated.startedAt`, else `lastState.terminated.startedAt`). From that start its deadline, `worker.attemptDeadlineSeconds` (21600), runs. The attempt records both times, `started_at` (the submit) and `started_running_at` (the driver start, clamped between the submit and the poll that read it), and the console's Maintenance tab shows how long it queued and how long it ran; a duration of an hour or more shows in hours. If the driver pods cannot be read, the attempt cannot see its driver start: at the queue wait limit a job still pending ends `queue_timed_out`, and one running or completed is taken as started at that poll (each failed read is logged as an error).

The wait in the queue has a limit of its own, `worker.queueWaitLimitSeconds` (86400, `GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS`). At the limit the worker polls the attempt once more: if that poll reads its driver start, the attempt runs on under its deadline from that start; a job that reads running or completed but whose driver start cannot be read is taken as started at that poll, so a completed one gets its callback grace and a running one its deadline from then; and a job that failed or went missing ends as any poll would. Only an attempt whose job is still pending with no driver start (or whose status cannot be read) is stopped (its Spark job is deleted and its pods are polled until none is live), ends `queue_timed_out` with failure class `queue_timeout`, and is not retried: its operation waits for the next plan. The worker polls a queued attempt every 30 s for the first 10 minutes and then every 10 minutes, and a running one every 30 s for the first 10 minutes after its driver starts and then every 5 minutes, which keeps the workflow history small. **A driver start is therefore seen up to one poll interval late** (the attempt still records the driver's own start time); the poll at the limit is what keeps a driver that started within the last interval from being stopped. The reconciliation's give-up bound for a run that never reports counts every attempt's queue wait limit as well as its deadline.

A manual run on a table whose run is in flight does not start a second one: it raises the priority of the run in flight, only upward (`P0` over `P1` over `P2` over `P3`), and a manual run with no priority means the table's current one. A lower or equal priority changes nothing. The operation that is running is not interrupted, and later operations are submitted at the new priority. An attempt that is still `queued` is replaced only when its job reads `PENDING` with no driver start: its job is deleted and submitted again at the new priority under the same attempt number, which does not count toward `worker.maxAttempts` and keeps the attempt's submit time and queue deadline. Every job delete (a requeue, a fence, the end of a run) uses foreground propagation: the SparkApplication stays readable, marked for deletion, until the pods and PodGroup it owns are gone, so the replacement is submitted only once the old job reads `NOT_FOUND` and has no live pods, and never meets the old PodGroup. A driver that starts between the check and the delete is killed with the job, and the attempt runs again, which the maintenance procedures allow; a result that killed job sends meanwhile is dropped, so only the replacement's result counts. A running attempt, and one whose driver has started, is left alone. The manual trigger is consumed once the raise is delivered. The run reports, when it ends, whether it left a raise unapplied (one that arrived after its last attempt ended, or whose record failed) and how many raises it had received; the reconciliation gives the manual trigger back, to be planned as a run of its own after this one, when the run left a raise unapplied or received fewer raises than were delivered to it (a raise that reached it after it built its report). The trigger is dropped instead when the plan that would run it fails, the table is skipped, nothing is planned, or the workflow is stopping. A run whose workflow closed without reporting is treated as finished and gives its trigger back: at once when the reconciliation execution that started it sees the close (a run already closed is never carried through continue-as-new); a run carried through continue-as-new when a raise cannot reach it and a lookup finds its workflow no longer running, otherwise at the give-up bound. A run that is given up gives its trigger back too, whether or not it reports after the cancel, because the cancel stopped its work. After a run reports, the reconciliation waits for its workflow to close before it starts the next, at most the report activity's worst case, so the table's one workflow id is free; a start that is refused after that is recorded as `run_start_failed`. Changing a table's own priority never touches a run in flight: it applies from the next plan.

`GET /v1/platform-settings` returns the platform's read-only settings in four groups (execution capacity, Spark sizes, cooldown and backoff, discovery), each a key, label, value, unit and one-sentence description built from a whitelist, so no secret can reach it; the console's Platform settings page (last in the nav) shows them. **The maintenance limits, cooldowns and back-off are set by the deployment, not by a policy:** the ConfigMap gives them to api and worker alike.

| Setting | Chart key | Env | Default | Meaning |
|---|---|---|---|---|
| `maintenance_attempt_deadline_seconds` | `worker.attemptDeadlineSeconds` | `GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS` | 21600 | How long one attempt may run, from its driver start |
| `maintenance_queue_wait_limit_seconds` | `worker.queueWaitLimitSeconds` | `GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS` | 86400 | How long one attempt may wait in its Volcano queue |
| `maintenance_max_attempts` | `worker.maxAttempts` | `GLAC_MAINTENANCE_MAX_ATTEMPTS` | 3 | Attempts per operation |
| `maintenance_rewrite_data_files_cooldown_seconds` | `worker.rewriteDataFilesCooldownSeconds` | `GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS` | 3600 | The least time between two compactions of one table |
| `maintenance_rewrite_manifests_cooldown_seconds` | `worker.rewriteManifestsCooldownSeconds` | `GLAC_MAINTENANCE_REWRITE_MANIFESTS_COOLDOWN_SECONDS` | 21600 | The least time between two manifest rewrites of one table |
| `maintenance_expire_snapshots_cooldown_seconds` | `worker.expireSnapshotsCooldownSeconds` | `GLAC_MAINTENANCE_EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS` | 21600 | The least time between two snapshot expiries of one table |
| `maintenance_remove_orphan_files_interval_seconds` | `worker.removeOrphanFilesIntervalSeconds` | `GLAC_MAINTENANCE_REMOVE_ORPHAN_FILES_INTERVAL_SECONDS` | 604800 | How often orphan files are removed from a table whose policy holds the block |
| `maintenance_failure_backoff_cap_seconds` | `worker.failureBackoffCapSeconds` | `GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS` | 86400 | The longest wait after repeated failures; each consecutive failure doubles the operation's cooldown up to it |

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryWorkflow` | schedule `table-discovery:catalog={catalog}` (Temporal appends the firing time); ad hoc `table-discovery:catalog={catalog}[:namespace={namespace}]:trigger=adhoc` | `{catalog}`; ad hoc `{catalog}[.{namespace}] · ad hoc` |
| `TableReconciliationWorkflow` | `table-reconciliation:table-uuid={uuid}` | `{catalog}.{namespace}.{table}` at first start |
| `TableMaintenanceWorkflow` | `table-maintenance:table-uuid={uuid}` (one per table, so a second start while a run is open is refused; stored on the run as `execution_ref`; the run keeps its `mr-` id) | `{catalog}.{namespace}.{table} · {operations}` |

## Call the API

```
kubectl port-forward service/table-maintenance-api 8000:8000 --namespace lakehouse-control-plane --context retail-lakehouse
curl http://localhost:8000/healthz
curl http://localhost:8000/v1/tables
```

No route needs authentication. The main routes, all under `/v1`:

| Route | Use |
|---|---|
| `GET, PUT /discovery-rules`, `GET /discovery-rules/catalogs` | the discovery rules, saved whole; first enabled match by `priority` wins, `action` is `include` or `exclude`; `PUT` carries the `version` it was edited from (409 when stale, 422 for equal priorities) and applies at once |
| `GET, POST /maintenance-policies`, `GET, PUT, DELETE /maintenance-policies/{name}`, `GET /maintenance-policies/{name}/versions/{version}` | versioned maintenance policies; the migration seeds `default`; `PUT` carries the `version`, and deleting `default` or an attached policy returns 409 |
| `GET, PUT, DELETE /maintenance-policies/{name}/mappings` | list where a policy is attached, attach it to a catalog, namespace or table (`{"target": {"type": "table", "path": ["iceberg", "e2e", "tm_e2e_orders"]}}`, replacing what is attached there) or detach it; a mapping whose target left the catalog is listed as orphaned |
| `GET /tables/{uuid}/applicable-policy`, `GET /applicable-policy?catalog=&namespace=` | the policy that applies after inheritance (table, then namespace, then catalog, then `default`) and the target it is attached to |
| `GET /tables?status=managed` | tables (`managed`, `unmanaged`, `dropped`), each with `last_committed_at` (the newest snapshot's commit time) and `last_discovered_at` (when a catalog scan last saw it); both null when unknown |
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`, optional `priority`; runs whole-table with the options of the applicable policy's blocks (an operation the policy leaves out runs with the platform's choices), ignores cooldowns; while a run is in flight it raises that run's priority instead of starting another |
| `GET /tables/{uuid}/table-maintenance-runs`, `GET /table-maintenance-runs/{run_id}` | run history with per-operation status and metrics |

Save the rule list (read `version` with `GET /v1/discovery-rules` first; the list replaces the old one, so send the existing rules too):

```
curl -X PUT http://localhost:8000/v1/discovery-rules -H 'Content-Type: application/json' \
  -d '{"version": 0, "rules": [{"priority": 10, "action": "include", "enabled": true,
       "catalogs": ["iceberg"], "namespaces": ["e2e"], "tables": ["tm_e2e_*"]}]}'
```

A policy describes the state a table is kept in. Its body has a `description`, `on`, `dry_run` and up to four operation blocks. `on.schedule.every_seconds` (60 to 604800) is how often the table is checked, and the optional `on.catalog_commit.debounce_seconds` (0 to 86400, default 300) checks the table a debounce after a commit; leave `catalog_commit` out and commits trigger nothing. Each operation (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`) is a block `{target, options}`; a block that is absent or `null` means the policy does not do that operation, and a policy may hold no block at all. Read `GET /v1/maintenance-policies/default` for a complete body, and drop the fields the server sets (`id`, `name`, `is_default`, `version`, `created_at`, `updated_at`) before sending it as a new policy with its own `name` (for an update, send `version` back instead); unknown keys return 422.

**`target` says when an operation is due, `options` only how it runs.** `target` is the state the table is kept in: `rewrite_data_files` holds `reducible_files.at_most` and `per` (`partition`, the default, or `table`), `rewrite_manifests` holds `small_manifests.at_most`, `expire_snapshots` holds `min_snapshots_to_keep` (at most 2147483647) and `max_snapshot_age_seconds` (at most 3153600000, 100 years), and `remove_orphan_files` holds `older_than_seconds` (86400 to 3153600000). An operation is due when the table is off its target, and the platform cooldown (see the settings above) holds it back after a run; orphan file removal has no cheap target, so its block alone makes it due on the platform interval. `per: partition` decides only whether compaction is due; a run compacts the whole table either way. A retention value the policy leaves out is the table's `history.expire.*` property, else Iceberg's default; a table age property over 100 years (Iceberg's `Long.MAX` "never by age") is read as 100 years. `options` are the arguments the Iceberg procedure runs with, a curated subset of each procedure's (the runtime's `README.md` lists them); an option left out is the procedure's default, and a key the platform owns (`where`, the target file size, `older_than`, `retain_last`) is refused. `dry_run` makes scheduled checks record what would run and start nothing; a manual run still runs.

A table's reconciliation checks the table when its schedule fires; when a commit window closes (the first commit not yet checked opens a window of the debounce, later commits join it without moving its end, and any other check but a manual run takes it, since a manual run looks only at the operations it names); and always, whatever `on` says, for a manual run, Reconcile now, a policy change and a table becoming managed (a discovery scan only keeps the workflow alive).

## End-to-end check

`e2e.sh` is a manual check, not part of `validate.sh`. It takes 20 to 40 minutes, mostly Spark start-up (each operation is its own SparkApplication, which downloads the Iceberg jars from Maven Central, so the cluster needs internet access).

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh
```

It:

1. issues a Trino client certificate for user `tm-e2e` (`task trino:issue-cert`) and port-forwards `service/trino` to `localhost:18445` (`TRINO_PORT`) for each query;
2. saves the discovery rule `include iceberg / e2e / tm_e2e_*` with `PUT /v1/discovery-rules`, prepended with the lowest priority minus one (reused if an enabled one exists);
3. creates `iceberg.e2e.tm_e2e_orders` (partitioned by `day(order_ts)`, `bucket(id, 4)`) and `iceberg.e2e.tm_e2e_regions` (partitioned by `region`) if missing, inserts 20 and 8 single-row commits, and deletes one order to add a delete file; half of the regions are `o'neil`;
4. waits up to 15 minutes for both tables to be `managed`, prints when each `table-reconciliation:table-uuid={uuid}` workflow's current run started next to the discovery schedule's recent runs (on a table's first run, a reconcile start before the next scheduled run means the event path found the table), then waits for running runs to finish (the attached `tm-e2e-regions` may already compact the regions table, which is why its counts are taken before discovery);
5. already before the inserts (right after `CREATE TABLE`), creates the policies `tm-e2e-orders` and `tm-e2e-regions` as copies of `default` (updated if they exist) and attaches them to their tables; `tm-e2e-orders` is a `dry_run` policy, so it is inert for scheduling while its blocks carry the values the manual run uses (`rewrite_data_files` `min_input_files: 1`, `expire_snapshots` `min_snapshots_to_keep: 1` and `max_snapshot_age_seconds: 60`, `remove_orphan_files` `older_than_seconds: 86400`), and `tm-e2e-regions` stays schedulable (`on.schedule.every_seconds: 300`, `on.catalog_commit.debounce_seconds: 60`, only a `rewrite_data_files` block with `reducible_files.at_most: 1`);
6. checks `GET /v1/tables/{uuid}/applicable-policy` of both tables, triggers all four operations on orders manually (a manual run plans every named operation, with the policy's options when its block holds them and the platform's choices when it does not), and lets a check of the regions table compact the whole table: the check when the table becomes managed, or the one when the commit window of its inserts closes, whichever finds it off target first (the platform's one-hour rewrite cooldown applies from a table's previous run, so a rerun waits for it, see below);
7. requires every operation of the new runs to be `succeeded` with `rewritten_data_files_count > 0`, the orders data file count (`$files`) and snapshot count (`$snapshots`) to decrease, `expire_snapshots` to delete files and the RustFS object count under the orders `data/` prefix (one-off `pgsty/mc` pod) to be at most before + files added by the rewrite − files expired (the raw count can grow, because `older_than` is fixed at plan time and the rewrite's partial-progress commits still reference the old files), the regions file count to decrease, every `rewrite_data_files` plan (read from the history of the run's maintenance workflow, whose ID the API returns as `execution_ref`) to carry no `where` filter, every succeeded attempt to have `started_running_at` between its `started_at` and `finished_at`, and the table's `table-reconciliation:table-uuid={uuid}` and `table-maintenance:table-uuid={uuid}` workflows to be found by `TableUuid`;
8. reads the orders `metadata` and `commits?limit=1000` and the regions `metrics/current` through the API and requires `total_data_files + total_delete_files` to equal the `$files` count (Trino's `$files` lists data and delete files), `snapshot_count` to equal the `$snapshots` count, the commits to be newest first, the regions `metrics.data_files` to be non-null and the compaction callback to report at least one rewritten data file (skipped when the callback was lost).

If a Spark driver cannot deliver its result callback (the API or its database is down), the polling fallback records the operation as `succeeded` with `{"completed_without_callback": 1}` and no procedure metrics; the check then relies on the `$files` count alone and says so. Only `[INFO]` progress lines are printed; on failure the full output is dumped. The script can be rerun: it reuses the tables, the rule and the policies, and a rerun adds new small files. **A rerun waits for the platform rewrite cooldown**: the regions compaction is due again only once the cooldown since its last compaction has passed, so on a rerun the script reads `maintenance_rewrite_data_files_cooldown_seconds` from `GET /v1/platform-settings` and waits that long plus the policy's schedule interval longer for the scheduled run. `remove_orphan_files` keeps files younger than one day, so it succeeds without deleting the files just written.

The e2e tables, the rule and the policies stay in place to show the scheduled path. To remove them:

```
curl -X PUT http://localhost:8000/v1/discovery-rules -H 'Content-Type: application/json' \
  -d '{"version": <version>, "rules": [<the other rules, without the e2e one>]}'
curl -X DELETE http://localhost:8000/v1/maintenance-policies/tm-e2e-orders/mappings -H 'Content-Type: application/json' \
  -d '{"target": {"type": "table", "path": ["iceberg", "e2e", "tm_e2e_orders"]}}'
trino> DROP TABLE iceberg.e2e.tm_e2e_orders; DROP TABLE iceberg.e2e.tm_e2e_regions; DROP SCHEMA iceberg.e2e;
task trino:delete-cert TRINO_USER=tm-e2e KUBE_CONTEXT=retail-lakehouse
```

Discovery then marks the tables `dropped` and their reconcile workflows end.

## Spark event logs

Every maintenance SparkApplication writes its Spark event log to the RustFS bucket `spark-event-logs` (wave `20-rustfs`, 3-day expiry): `spark.eventLog.enabled=true`, `spark.eventLog.dir=s3a://spark-event-logs/` (`GLAC_SPARK__EVENT_LOG_DIR`), `compress=true` with `zstd`, `logStageExecutorMetrics=true` and rolling at `128m`. S3A gets `fs.s3a.endpoint` / `fs.s3a.endpoint.region` from the catalog settings, `path.style.access`, `connection.ssl.enabled=false` for an `http://` endpoint and `EnvironmentVariableCredentialsProvider`, which reads `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the `table-maintenance-s3` Secret the driver and executor already load. The jars are `hadoop-aws` 3.4.1 (the Hadoop bundled in `apache/spark:4.0.0`, `GLAC_SPARK__HADOOP_VERSION`) and `s3-transfer-manager` 2.33.0 (`GLAC_SPARK__AWS_SDK_VERSION`): `iceberg-aws-bundle` 1.10.1 already ships AWS SDK v2.33.0 but not the transfer manager, which S3A uses for uploads and the rename copy.

Each run leaves `eventlog_v2_<appId>/` with `events_<N>_<appId>.zstd` files and an `appstatus_<appId>` marker. Spark creates `appstatus_<appId>.inprogress` at start and renames it (S3 CopyObject + DeleteObject) at `spark.stop()`; the bucket notification sends only that copy (`s3:ObjectCreated:Copy`, prefix `eventlog_v2_`) to the Kafka topic `spark-event-log-completions` in `kafka`, so the topic gets one message per finished application. The runtime stops the Spark session before posting its result callback, because the workflow deletes a run's SparkApplications as soon as the last callback arrives: with the old order a run's last driver could be killed inside `spark.stop()` and its `.inprogress` marker was never renamed. A driver that crashes or is killed still leaves `.inprogress` and sends no message.

Recording an attempt that Spark ended (its result callback, or a FAILED SparkApplication) reads the attempt's SparkApplication and pods for evidence and then, with the application id, the two possible markers in one listing: `appstatus_<appId>` means the event log finished (`event_log_finished: true`), only `appstatus_<appId>.inprogress` means it did not (`false`), neither or a read failure means unknown (`null`). Timed-out, cancelled and missing attempts are not read (their SparkApplication was deleted first) and record `null`. Executors are kept after they end (`spark.kubernetes.executor.deleteOnTermination=false`) so an executor's OOM kill can still be read; the run deletes its SparkApplications, and with them every pod, when it ends. The driver container uses `terminationMessagePolicy: FallbackToLogsOnError`, so a driver that dies leaves the tail of its log as its termination message.

Event contract, from a `rewrite_data_files` run of the e2e (Kafka key, then value; the record timestamp is the broker's append time, use `eventTime`; `principalId` replaced here):

```
spark-event-logs/eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1%2Fappstatus_spark-5c92a6295b194c75832331bc5bfc3aa1
```

```json
{
  "EventName": "s3:ObjectCreated:Copy",
  "Key": "spark-event-logs/eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1/appstatus_spark-5c92a6295b194c75832331bc5bfc3aa1",
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "rustfs:s3",
      "awsRegion": "",
      "eventTime": "2026-11-03T17:56:37.450Z",
      "eventName": "s3:ObjectCreated:Copy",
      "userIdentity": {
        "principalId": "<RustFS access key id>"
      },
      "requestParameters": {
        "connection": "Keep-Alive",
        "content-type": "application/octet-stream",
        "x-amz-date": "20261103T175637Z",
        "host": "rustfs.object-storage.svc.cluster.local:9000",
        "content-length": "0",
        "authorization": "***redacted***",
        "user-agent": "Hadoop 3.4.1 aws-sdk-java/2.33.0 md/io#sync md/http#Apache ua/2.1 api/S3#2.33.x os/Linux#6.8.0-90-generic lang/java#17.0.15 md/OpenJDK_64-Bit_Server_VM#17.0.15+6 md/vendor#Eclipse_Adoptium md/en_US md/scala/2.13.16 cfg/auth-source#env m/F,N,N,G",
        "amz-sdk-request": "attempt=1; max=6",
        "x-amz-content-sha256": "***redacted***",
        "x-amz-copy-source-if-match": "\"d41d8cd98f00b204e9800998ecf8427e\"",
        "x-amz-metadata-directive": "REPLACE",
        "x-request-id": "d7123c68-fa5e-4930-85c2-33be9f0956d1",
        "principalId": "<RustFS access key id>",
        "referer": "https://audit.example.org/hadoop/1/op_rename/3077fa29-343e-45e5-93ed-1a7d848971dc-00000014/?op=op_rename&p1=s3a://spark-event-logs/eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1/appstatus_spark-5c92a6295b194c75832331bc5bfc3aa1.inprogress&pr=spark&p2=s3a://spark-event-logs/eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1/appstatus_spark-5c92a6295b194c75832331bc5bfc3aa1&ps=57a6ae8d-74c2-4a7b-b620-d1c563f65ba6&id=3077fa29-343e-45e5-93ed-1a7d848971dc-00000014&t0=23&fs=3077fa29-343e-45e5-93ed-1a7d848971dc&t1=23&ts=1793728597308",
        "x-amz-copy-source": "spark-event-logs/eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1/appstatus_spark-5c92a6295b194c75832331bc5bfc3aa1.inprogress",
        "amz-sdk-invocation-id": "abc40a28-47de-026d-4f72-1d98368f057e"
      },
      "responseElements": {
        "x-amz-request-id": "d7123c68-fa5e-4930-85c2-33be9f0956d1",
        "x-amz-id-2": ""
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "Config",
        "bucket": {
          "name": "spark-event-logs",
          "ownerIdentity": {
            "principalId": "<RustFS access key id>"
          },
          "arn": "arn:aws:s3:::spark-event-logs"
        },
        "object": {
          "key": "eventlog_v2_spark-5c92a6295b194c75832331bc5bfc3aa1%2Fappstatus_spark-5c92a6295b194c75832331bc5bfc3aa1",
          "size": 0,
          "eTag": "d41d8cd98f00b204e9800998ecf8427e",
          "contentType": "application/octet-stream",
          "userMetadata": {
            "content-type": "application/octet-stream"
          },
          "sequencer": "18E49AA7E1F4B8EB"
        }
      },
      "source": {
        "host": "rustfs.object-storage.svc.cluster.local:9000",
        "port": "9000",
        "userAgent": "Hadoop 3.4.1 aws-sdk-java/2.33.0 md/io#sync md/http#Apache ua/2.1 api/S3#2.33.x os/Linux#6.8.0-90-generic lang/java#17.0.15 md/OpenJDK_64-Bit_Server_VM#17.0.15+6 md/vendor#Eclipse_Adoptium md/en_US md/scala/2.13.16 cfg/auth-source#env m/F,N,N,G"
      }
    }
  ]
}
```

The application id is the `eventlog_v2_` directory in `Key` (or `Records[0].s3.object.key` URL-decoded); delivery is at least once, so consumers must be idempotent on that key. Read the topic:

```
kubectl exec kafka-cluster-dual-role-0 --namespace kafka --context retail-lakehouse -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic spark-event-log-completions --from-beginning --property print.key=true
```

## Logs

```
kubectl logs deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse
```
