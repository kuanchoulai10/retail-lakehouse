# Lakehouse Control Plane

Wave 25. Creates the `lakehouse-control-plane` and `lakehouse-maintenance-operations` namespaces and deploys the table maintenance control plane as the Helm release `table-maintenance` (`chart/`).

## Deployed Resources

```
Namespace: lakehouse-control-plane
  Deployment table-maintenance-db             PostgreSQL 17.11 (PVC, Recreate), Service table-maintenance-db:5432
  Job        table-maintenance-migrate-<rev>  creates the schema, seeds the "default" maintenance and discovery policies
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

The `migrate` Job is a regular Job named with the Helm release revision, so each upgrade runs it again. A pre-install hook would run before the PostgreSQL Deployment exists. The Job waits for `pg_isready`. The api, worker and event-consumer pods have an init container that waits until the `default` maintenance policy and the `default` discovery policy (`dp-00000000000000000000000000`) both exist, which means the migration finished.

## Configuration

All settings are `GLAC_*` environment variables rendered from `chart/values.yaml` into the ConfigMap `table-maintenance-config` (temporal address, catalog URI, S3 endpoint, Kafka, Spark, `GLAC_DISCOVERY_INTERVAL_SECONDS`, `GLAC_MAINTENANCE_*`). Secrets come from `table-maintenance-db`, `table-maintenance-polaris-credential` and `table-maintenance-s3`. **No setting names the catalogs to scan: the scanned catalogs follow the discovery policy attachments.** A catalog is scanned while a discovery policy attached to it, or to a namespace or table in it, can manage tables; `GLAC_DISCOVERY_INTERVAL_SECONDS` only sets how often each scanned catalog is scanned.

### Spark sizes

Every maintenance attempt runs at one of three sizes, set under `spark.sizes` in `chart/values.yaml` and rendered as `GLAC_SPARK__SIZE_<S|M|L>__DRIVER_MEMORY`, `__EXECUTOR_MEMORY` and `__EXECUTOR_INSTANCES`. Driver and executor stay capped at one core; memory overhead is Spark's default (`max(384Mi, 0.4 × memory)` for a Python application), so the pod requests are:

| Size | Driver memory | Executor memory | Executors | Pod requests, driver + executor |
|---|---|---|---|---|
| S | `768m` | `768m` | 1 | 1152Mi + 1152Mi = 2304Mi |
| M | `1g` | `1536m` | 1 | 1434Mi + 2150Mi = 3584Mi |
| L | `1536m` | `2g` | 1 | 2150Mi + 2867Mi = 5017Mi |

An L job fits on the 8-CPU / 26 GB node only alone; next to another Spark job it stays queued while its queue-wait clock runs (its attempt deadline starts only once its driver runs). A partial override (one `GLAC_SPARK__SIZE_L__EXECUTOR_MEMORY`) keeps the other values of that size.

An operation starts at the size its table last succeeded at (S for a table that never did). Each failed attempt is classified when it is recorded: `oom` (a driver or executor container `OOMKilled` or exit 137, an executor exit 52, or `java.lang.OutOfMemoryError` / `OOMKilled` / `exit code 52` in the error or a driver termination message; container exits count only when Spark itself ended the attempt, since the platform's own deletes also exit 137), `timeout`, `queue_timeout`, `commit_conflict`, `permanent` (missing table, forbidden), `cancelled` or `other`. An attempt's deadline and queue wait are timed apart (see Queue wait and run time); one stopped in the queue is not retried. An `oom` retries at the next size; `permanent` is not retried; other failures retry at the same size, within `worker.maxAttempts` (3) attempts. An `oom` at L stops the operation and marks it **needs attention** on the table: reconcile stops planning it until a manual run of it, or until another policy (or policy version, or the same policy attached elsewhere) applies to the table than the one its run was planned under. The next reconcile after such a change clears the mark for good, so going back to the earlier policy does not bring the block back; until that reconcile, the table API still shows the mark. A success records the attempt's size, and the Spark runtime reports the peak heap the driver and the busiest executor used, in bytes (reported as `peak_coordinator_memory_bytes` and `peak_worker_memory_bytes`, read from the driver's own Spark UI REST API on localhost before the session stops). A success counts toward stepping down only when both peaks fit within 70% of the next smaller size's driver and executor memory (as set in `spark.sizes`); three such successes in a row at the remembered size step it down one size, and a role with no measured peak never counts. The run API lists every attempt with its size, failure class, event-log state and next step, and the console's Maintenance tab shows them.

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

A manual run on a table whose run is in flight does not start a second one: it raises the priority of the runs in flight, the one running and the ones still pending, only upward (`P0` over `P1` over `P2` over `P3`), and a manual run with no priority means the table's current one. A lower or equal priority changes nothing. The run that is running is not interrupted, and the runs after it are submitted at the new priority. An attempt that is still `queued` is replaced only when its job reads `PENDING` with no driver start: its job is deleted and submitted again at the new priority under the same attempt number, which does not count toward `worker.maxAttempts` and keeps the attempt's submit time and queue deadline. Every job delete (a requeue, a fence, the end of a run) uses foreground propagation: the SparkApplication stays readable, marked for deletion, until the pods and PodGroup it owns are gone, so the replacement is submitted only once the old job reads `NOT_FOUND` and has no live pods, and never meets the old PodGroup. The same holds between runs: the next run submits only after the previous run's Spark jobs are gone, and the workflow reports to the reconciliation only after the last run's jobs are gone. A driver that starts between the check and the delete is killed with the job, and the attempt runs again, which the maintenance procedures allow; a result that killed job sends meanwhile is dropped, so only the replacement's result counts. A running attempt, and one whose driver has started, is left alone. The manual trigger is consumed once the raise is delivered. The run reports, when it ends, whether it left a raise unapplied (one that arrived after its last attempt ended, or whose record failed) and how many raises it had received; the reconciliation gives the manual trigger back, to be planned as a run of its own after this one, when the run left a raise unapplied or received fewer raises than were delivered to it (a raise that reached it after it built its report). The trigger is dropped instead when the plan that would run it fails, the table is skipped, nothing is planned, or the workflow is stopping. A run whose workflow closed without reporting is treated as finished and gives its trigger back: at once when the reconciliation execution that started it sees the close (a run already closed is never carried through continue-as-new); a run carried through continue-as-new when a raise cannot reach it and a lookup finds its workflow no longer running, otherwise at the give-up bound. A run that is given up gives its trigger back too, whether or not it reports after the cancel, because the cancel stopped its work. After a run reports, the reconciliation waits for its workflow to close before it starts the next, at most the report activity's worst case, so the table's one workflow id is free; a start that is refused after that is recorded as `run_start_failed`. The runs of a plan are created, `pending`, by the reconciliation in one transaction before it starts the child, so a reconciliation never links a run that does not exist: when that create fails no child starts and the reconciliation records `run_start_failed` with no run, and when the child is refused its start the runs just created are skipped (`skip_reason` "the table's maintenance workflow could not be started"). Changing a table's own priority never touches a run in flight: it applies from the next plan.

`GET /v1/platform-settings` returns the platform's read-only settings in five groups (execution capacity, Spark sizes, cooldown and backoff, compaction partition selection, discovery), each a key, label, value, unit and one-sentence description built from a whitelist, so no secret can reach it; the console's Platform settings page (last in the nav) shows them. **The maintenance limits, cooldowns and back-off are set by the deployment, not by a policy:** the ConfigMap gives them to api and worker alike.

| Setting | Chart key | Env | Default | Meaning |
|---|---|---|---|---|
| `maintenance_attempt_deadline_seconds` | `worker.attemptDeadlineSeconds` | `GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS` | 21600 | How long one attempt may run, from its driver start |
| `maintenance_queue_wait_limit_seconds` | `worker.queueWaitLimitSeconds` | `GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS` | 86400 | How long one attempt may wait in its Volcano queue |
| `maintenance_max_attempts` | `worker.maxAttempts` | `GLAC_MAINTENANCE_MAX_ATTEMPTS` | 3 | Attempts per operation |
| `maintenance_rewrite_data_files_cooldown_seconds` | `worker.rewriteDataFilesCooldownSeconds` | `GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS` | 3600 | The least time between two compactions of one table |
| `maintenance_rewrite_manifests_cooldown_seconds` | `worker.rewriteManifestsCooldownSeconds` | `GLAC_MAINTENANCE_REWRITE_MANIFESTS_COOLDOWN_SECONDS` | 21600 | The least time between two manifest rewrites of one table |
| `maintenance_expire_snapshots_cooldown_seconds` | `worker.expireSnapshotsCooldownSeconds` | `GLAC_MAINTENANCE_EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS` | 21600 | The least time between two snapshot expiries of one table |
| `maintenance_remove_orphan_files_interval_seconds` | `worker.removeOrphanFilesIntervalSeconds` | `GLAC_MAINTENANCE_REMOVE_ORPHAN_FILES_INTERVAL_SECONDS` | 604800 | How often orphan files are removed from a table whose policy holds the block |
| `maintenance_compaction_partitions_per_job` | `worker.compactionPartitionsPerJob` | `GLAC_MAINTENANCE_COMPACTION_PARTITIONS_PER_JOB` | 10 | The most partitions one scheduled compaction rewrites; those over the target for the longest wait go first, oldest first, then the most reducible first |
| `maintenance_compaction_quiet_seconds` | `worker.compactionQuietSeconds` | `GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS` | 120 | How long after its last write a partition waits before it is compacted; 0 never waits |
| `maintenance_compaction_max_quiet_wait_seconds` | `worker.compactionMaxQuietWaitSeconds` | `GLAC_MAINTENANCE_COMPACTION_MAX_QUIET_WAIT_SECONDS` | 3600 | How long a partition over the target may keep waiting for quiet before it is compacted anyway; a partition over the target this long also goes first under the per-job cap, oldest first; 0 means nothing waits |
| `maintenance_failure_backoff_cap_seconds` | `worker.failureBackoffCapSeconds` | `GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS` | 86400 | The longest wait after repeated failures; each consecutive failure doubles the operation's cooldown up to it |

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

**A discovery schedule exists only while its catalog is scanned.** A fresh cluster has none until a managing discovery policy is attached. After an update, an attach or a detach, the API rescans each affected catalog and syncs the schedules (best effort: a failure is logged and the request still succeeds); a catalog that stops being scanned gets one final scan, which unmanages its managed tables, and then loses its schedule. The worker syncs the schedules at every start, before it polls, and a failure there stops the start: it creates the missing ones, gives each catalog that left (one with a schedule or managed tables but no managing attachment) its final scan, and deletes the extra ones.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryWorkflow` | schedule `table-discovery:catalog={catalog}` (Temporal appends the firing time); ad hoc `table-discovery:catalog={catalog}[:namespace={namespace}]:trigger=adhoc`; the scan after a discovery policy change `table-discovery:catalog={catalog}:trigger=policy-changed:change={id}` (a fresh 32-hex id per change, so a change never joins a scan that read older settings); the final scan the worker start gives a catalog it stops scanning `table-discovery:catalog={catalog}:trigger=schedule-retired:change={id}` | `{catalog}`; ad hoc `{catalog}[.{namespace}] · ad hoc` |
| `TableReconciliationWorkflow` | `table-reconciliation:table-uuid={uuid}` | `{catalog}.{namespace}.{table}` at first start |
| `TableMaintenanceWorkflow` | `table-maintenance:table-uuid={uuid}` (one per table, so a second start while a plan is open is refused; runs the plan's runs, one per operation, in order; each run keeps its `mr-` id and the execution as `execution_ref`) | `{catalog}.{namespace}.{table} · {operations}` |

## Call the API

```
kubectl port-forward service/table-maintenance-api 8000:8000 --namespace lakehouse-control-plane --context retail-lakehouse
curl http://localhost:8000/healthz
curl http://localhost:8000/v1/tables
```

No route needs authentication. The main routes, all under `/v1`:

| Route | Use |
|---|---|
| `GET, POST /discovery-policies`, `GET, PUT, DELETE /discovery-policies/{name}`, `GET /discovery-policies/{name}/versions/{version}` | versioned discovery policies; the migration seeds `default` (`dp-00000000000000000000000000`, no rules, manages nothing), which cannot change or be deleted (409); a policy is a `description`, ordered `rules` (the first whose `conditions` all hold decides) and a `no_match_outcome`, each outcome `manage` or `unmanage`; a condition is `{attribute, operator, values}` with `attribute` `namespace` or `table_name` and `operator` `glob`; a rule sent without `id` gets a `dr-` id, and an update may name only ids of the current version (422 otherwise); `PUT` carries the `version` it was edited from (409 when stale), and deleting an attached policy returns 409 |
| `GET, PUT /discovery-policies/{name}/attachments`, `DELETE /discovery-policies/{name}/attachments/{attachment_id}` | list where a discovery policy is attached, attach it to a catalog, namespace or table (`{"target": {"type": "namespace", "path": ["iceberg", "e2e"]}}`, replacing what is attached there and keeping that attachment's `da-` id) or detach it by id; a table follows its nearest attachment (table, then namespaces deepest first, then catalog, then `default`), which replaces its parents whole; a target that does not exist is 404 (an empty catalog or namespace exists), and a catalog the platform's credential cannot read is 403 |
| `GET /scanned-catalogs` | the catalogs a managing discovery policy is attached in, by name, each with `last_discovered_at` and its current `failure` (`{reason, detail, failed_at}`, `reason` `cannot_access` or `not_found`, or null) |
| `GET, POST /maintenance-policies`, `GET, PUT, DELETE /maintenance-policies/{name}`, `GET /maintenance-policies/{name}/versions/{version}` | versioned maintenance policies; the migration seeds `default`; `PUT` carries the `version`, and deleting `default` or an attached policy returns 409 |
| `GET, PUT /maintenance-policies/{name}/attachments`, `DELETE /maintenance-policies/{name}/attachments/{attachment_id}` | list where a maintenance policy is attached, attach it to a catalog, namespace or table (`{"target": {"type": "table", "path": ["iceberg", "e2e", "tm_e2e_orders"]}}`, replacing what is attached there and keeping that attachment's `pa-` id) or detach it by id; an attachment whose target left the catalog is listed as orphaned |
| `GET /tables/{uuid}/effective-policies`, `GET /effective-policies?catalog=&namespace=&table=` | the policy of each kind that applies after inheritance (table, then namespaces deepest first, then catalog, then `default`), as `{"policies": [maintenance, discovery]}`; each entry names the policy (`policy_id`, `policy_name`, its latest `version`, `description`), the `target` it is attached to and the `attachment_id` (both null for the platform default), the maintenance entry adds `dry_run` and the discovery entry `no_match_outcome`; by uuid, a table maintenance has no record of is 404; by location (namespace dot-joined), a catalog, namespace or table the catalog does not hold is 404 and a catalog the platform cannot read is 403 |
| `GET /tables?status=managed` | tables (`managed`, `unmanaged`, `dropped`), each with `last_committed_at` (the newest snapshot's commit time) and `last_discovered_at` (when a catalog scan last saw it); both null when unknown |
| `GET /table-metrics` | the Prometheus exposition of every managed table's current metrics (17 gauge series per table, text format 0.0.4); hidden from the OpenAPI schema, since only the Prometheus of wave `26-table-metrics-prometheus` reads it, every 30 s |
| `GET /tables/{uuid}/metrics/current` | the table's latest saved metrics (files by content type, data size and records, delete records, reducible files, manifests and their entries, snapshots) and when the reconcile observed them; `observed_at` and `metrics` are null for a table not reconciled yet or not managed; 404 for an unknown table |
| `GET /tables/{uuid}/metrics?range=1h\|3h\|6h` | the same metrics over time, read from that Prometheus (default `6h`, one point per 30 s / 90 s / 180 s; a gap is `null`); 404 for an unknown table, 502 with the reason when Prometheus cannot answer. The URL comes from `metrics.prometheusUrl` in `chart/values.yaml` (`GLAC_METRICS__PROMETHEUS_URL`) |
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`, optional `priority`; runs whole-table with the options of the applicable policy's blocks (an operation the policy leaves out runs with the platform's choices), ignores cooldowns; while a run is in flight it raises that run's priority instead of starting another |
| `GET /tables/{uuid}/table-maintenance-runs`, `GET /table-maintenance-runs/{run_id}` | run history, one run per operation, with what its job does (`settings`, and `partitions` for a compaction), procedure numbers (`metrics`) and attempts |
| `POST /table-maintenance-runs/{run_id}/result` | the callback a Spark job posts for one attempt of the run; the run names its operation, and a body that names another one is refused with 422 |
| `GET /tables/{uuid}/reconciliations`, `GET /table-reconciliations/{id}` | the table's reconciliation records, newest first, and one record by id; each started operation names the `run_id` of its run |

Create a discovery policy, then attach it; the attach makes the catalog scanned and starts its scan:

```
curl -X POST http://localhost:8000/v1/discovery-policies -H 'Content-Type: application/json' \
  -d '{"name": "tm-e2e", "no_match_outcome": "unmanage", "rules": [{"outcome": "manage",
       "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["tm_e2e_*"]}]}]}'
curl -X PUT http://localhost:8000/v1/discovery-policies/tm-e2e/attachments -H 'Content-Type: application/json' \
  -d '{"target": {"type": "namespace", "path": ["iceberg", "e2e"]}}'
```

A policy describes the state a table is kept in. Its body has a `description`, `on`, `dry_run` and up to four operation blocks. `on.schedule.every_seconds` (60 to 604800) is how often the table is checked, and the optional `on.catalog_commit.debounce_seconds` (0 to 86400, default 300) checks the table a debounce after a commit; leave `catalog_commit` out and commits trigger nothing. Each operation (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`) is a block `{target, options}`; a block that is absent or `null` means the policy does not do that operation, and a policy may hold no block at all. Read `GET /v1/maintenance-policies/default` for a complete body, and drop the fields the server sets (`id`, `name`, `is_default`, `version`, `created_at`, `updated_at`) before sending it as a new policy with its own `name` (for an update, send `version` back instead); unknown keys return 422.

**`target` says when an operation is due, `options` only how it runs.** `target` is the state the table is kept in: `rewrite_data_files` holds `reducible_files.at_most` and `per` (`partition`, the default, or `table`), `rewrite_manifests` holds `small_manifests.at_most`, `expire_snapshots` holds `min_snapshots_to_keep` (at most 2147483647) and `max_snapshot_age_seconds` (at most 3153600000, 100 years), and `remove_orphan_files` holds `older_than_seconds` (86400 to 3153600000). An operation is due when the table is off its target, and the platform cooldown (see the settings above) holds it back after a run; orphan file removal has no cheap target, so its block alone makes it due on the platform interval. **A scheduled `per: partition` compaction rewrites only the partitions over the target.** A check picks at most `worker.compactionPartitionsPerJob` of them (10): first those that have been over the target for `worker.compactionMaxQuietWaitSeconds` (oldest first), then the rest, the most reducible files first. The run's `rewrite_data_files` passes one `where` clause per partition spec; the partitions it leaves out wait for the next check that `on:` and the rewrite cooldown allow, so a partition waits at most about the longest wait plus the checks the overdue partitions ahead of it need. A partition written within `worker.compactionQuietSeconds` (120) waits too, so a compaction does not collide with a writer; once a partition has been over the target for `worker.compactionMaxQuietWaitSeconds` (3600) it stops waiting. When every partition over the target waits, the check records the verdict and result `waiting_for_writes` with `next_eligible_at`, and starts nothing. `per: table` ignores the quiet period, and a manual run always compacts the whole table. `GET /v1/table-maintenance-runs/{id}` and the run lists carry `partitions` on each compaction run, the partitions it rewrites per spec (`[{spec_id, fields, partitions}]`, `[]` for the whole table). A retention value the policy leaves out is the table's `history.expire.*` property, else Iceberg's default; a table age property over 100 years (Iceberg's `Long.MAX` "never by age") is read as 100 years. `options` are the arguments the Iceberg procedure runs with, a curated subset of each procedure's (the runtime's `README.md` lists them); an option left out is the procedure's default, and a key the platform owns (`where`, the target file size, `older_than`, `retain_last`) is refused. `dry_run` makes scheduled checks record what would run and start nothing; a manual run still runs.

A table's reconciliation checks the table when its schedule fires; when a commit window closes (the first commit not yet checked opens a window of the debounce, later commits join it without moving its end, and any other check but a manual run takes it, since a manual run looks only at the operations it names); and always, whatever `on` says, for a manual run, Reconcile now, a policy change and a table becoming managed (a discovery scan only keeps the workflow alive).

## End-to-end check

The e2e is a pytest package, `src/data-platform/backend/e2e/`, that checks the deployed platform from outside: it imports none of the backend's code (import-linter contract `e2e-black-box`), talks to the API, Polaris, Temporal and RustFS as a client, and needs no query engine, so it runs with Trino stopped. It runs in the cluster as one pod, built from `table-maintenance-e2e`, an image on top of the production backend image that adds only pytest, `pyiceberg-core` and the scenarios (`e2e.Dockerfile`; the backend image's tag ignores `e2e/` and the e2e image files, so changing a scenario does not redeploy the platform).

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e/run.sh critical   # minutes
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e/run.sh full       # about 20 minutes
```

`task gates:nightly:e2e-full-test KUBE_CONTEXT=…` runs `full`, and `task gates:pre-merge:e2e-critical-test KUBE_CONTEXT=…` runs `critical` (without `KUBE_CONTEXT` it prints its `TODO://` for the ephemeral platform). `run.sh` builds the images (`build.sh`), starts the pod `table-maintenance-e2e-<8 hex>` in `lakehouse-control-plane` from `e2e/pod.yaml`, follows its log (attaching again when the stream drops while the scenarios run) and exits with the scenarios' exit code; the pod is deleted on every exit. It refuses to start while another e2e pod runs on the cluster, since runs share the `tm-e2e` principal and each removes what an earlier one left. A pod that cannot start (a missing image, a failed init container) fails the runner within 300 s (`START_TIMEOUT_SECONDS`) with the pod's events, and `activeDeadlineSeconds` bounds a run (1200 s critical, 7200 s full).

**The e2e has its own Polaris principal.** The pod's init container alone holds the platform's credential (`table-maintenance-polaris-credential`): it runs `python -m e2e.setup_principal`, which keeps or creates principal `tm-e2e` with principal role and catalog role `tm_e2e` (`CATALOG_MANAGE_CONTENT` on `iceberg`) and the `service_admin` principal role (to read back the catalogs the round trip creates), resets its credentials (Polaris lets only a principal rotate its own) and writes them to an in-memory volume the scenarios read. The principal stays between runs; its credentials change on each. Storage is read with the RustFS key in `table-maintenance-s3`, the platform's only account.

| Marker | Scenario | What it checks |
|---|---|---|
| `critical` | `test_platform_answers.py` | the API lists the catalog and its namespaces, the e2e principal reads `iceberg` with PyIceberg, Temporal describes the platform's namespace |
| `critical` | `test_catalog_round_trip.py` | a catalog `tm_e2e_catalog_<suffix>` at `s3://tm-e2e-catalogs/<catalog>`, two namespaces, a `day(order_ts)` table at a custom location, a generic table and a view, each written through the API and read back from Polaris; the stale-update 409s; the non-empty namespace delete passes Polaris's status and message; each delete is followed by Polaris's 404 |
| `full` | `test_scheduled_partition_compaction.py` | a `region`-partitioned table with four appends (`north`, `o'neil`) under a policy of one reducible file per partition, checked every 300 s: the discovery schedule appears, a scheduled compaction succeeds with timed attempts and compacts spec 0's partitions including `o'neil`, the effective policies are the table's and its namespace's, the file count falls, current metrics carry `data_files` |
| `full` | `test_manual_maintenance.py` | an orders table with 20 single-row appends and a delete under a `dry_run` policy; 65 s after the last write a manual request runs all four operations: one run per operation of one plan, in plan order, timed, a whole-table compaction (`partitions == []`), linked in the reconciliation; reconcile now is recorded; files, snapshots and the objects under `data/` shrink as the runs' metrics account for; the catalog API's metadata agrees with PyIceberg's counts; commits come newest first; Temporal finds both workflows by `TableUuid`; every id the API returned is prefixed (ADR 0011) |

`full` runs every scenario (`-m "critical or full"`). **Each scenario uses names of its own run and undoes what it made, passed or failed.** A full scenario's namespace is `e2e_<suffix>_<scenario>` with a discovery policy `tm-e2e-<suffix>-<scenario>` attached to it; its cleanup detaches and deletes the discovery policy, waits until the table is unmanaged and its reconciliation stopped (so the platform default never plans a job on a half-removed table), detaches and deletes the maintenance policy, drops the table and removes its storage, then removes the namespace's storage and drops the namespace. A cleanup step that fails fails the scenario, naming the step. **A run that is cut short still cleans up**: a SIGTERM (the pod's deadline, an eviction, a delete) interrupts pytest, which tears down the running scenario's cleanup within the pod's 900 s grace period; and before any scenario starts, every run removes what an earlier run left under the e2e's own names (`OwnedNames`: namespaces `e2e_<suffix>_<scenario>`, policies `tm-e2e-<scenario>-<suffix>` and `tm-e2e-<suffix>-<scenario>`, catalogs `tm_e2e_catalog_<suffix>` and their storage), in the same order, and prints each removal. A scenario's namespace storage is the namespace's own `location`, refused when it is not the namespace's directory, so a cleanup never removes a wider prefix. The platform's own records of the dropped tables (the `dropped` table, its runs and reconciliations) stay: the platform keeps that history. If a Spark driver cannot deliver its result callback, the polling fallback records the run `succeeded` with `{"completed_without_callback": 1}`; the checks of the numbers that callback would have sent are then skipped.

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
