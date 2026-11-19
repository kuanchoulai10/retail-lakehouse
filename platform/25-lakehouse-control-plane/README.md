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

All settings are `GLAC_*` environment variables rendered from `chart/values.yaml` into the ConfigMap `table-maintenance-config` (temporal address, catalog URI and names, S3 endpoint, Kafka, Spark, `GLAC_ADMISSION_LIMIT`, `GLAC_DISCOVERY_INTERVAL_SECONDS`, `GLAC_COMPACTION__*`, `GLAC_SCHEDULER__*`). Secrets come from `table-maintenance-db`, `table-maintenance-polaris-credential` and `table-maintenance-s3`.

### Spark sizes

Every maintenance attempt runs at one of three sizes, set under `spark.sizes` in `chart/values.yaml` and rendered as `GLAC_SPARK__SIZE_<S|M|L>__DRIVER_MEMORY`, `__EXECUTOR_MEMORY` and `__EXECUTOR_INSTANCES`. Driver and executor stay capped at one core; memory overhead is Spark's default (`max(384Mi, 0.4 × memory)` for a Python application), so the pod requests are:

| Size | Driver memory | Executor memory | Executors | Pod requests, driver + executor |
|---|---|---|---|---|
| S | `768m` | `768m` | 1 | 1152Mi + 1152Mi = 2304Mi |
| M | `1g` | `1536m` | 1 | 1434Mi + 2150Mi = 3584Mi |
| L | `1536m` | `2g` | 1 | 2150Mi + 2867Mi = 5017Mi |

An L job fits on the 8-CPU / 26 GB node only alone; next to another Spark job it stays Pending while its attempt clock runs. A partial override (one `GLAC_SPARK__SIZE_L__EXECUTOR_MEMORY`) keeps the other values of that size.

An operation starts at the size its table last succeeded at (S for a table that never did). Each failed attempt is classified when it is recorded: `oom` (a driver or executor container `OOMKilled` or exit 137, an executor exit 52, or `java.lang.OutOfMemoryError` / `OOMKilled` / `exit code 52` in the error or a driver termination message; container exits count only when Spark itself ended the attempt, since the platform's own deletes also exit 137), `timeout`, `commit_conflict`, `permanent` (missing table, forbidden), `cancelled` or `other`. An `oom` retries at the next size; other failures retry at the same size, within `worker.maxAttempts` (3) attempts. An `oom` at L stops the operation and marks it **needs attention** on the table: reconcile stops planning it until a manual run of it, or until another policy (or policy version, or the same policy attached elsewhere) applies to the table than the one its run was planned under. The next reconcile after such a change clears the mark for good, so going back to the earlier policy does not bring the block back; until that reconcile, health and the table API both still show the mark. A success records the attempt's size, and the Spark runtime reports the peak heap the driver and the busiest executor used, in bytes (`peak_driver_heap_bytes`, `peak_executor_heap_bytes`, read from the driver's own Spark UI REST API on localhost before the session stops). A success counts toward stepping down only when both peaks fit within 70% of the next smaller size's driver and executor memory (as set in `spark.sizes`); three such successes in a row at the remembered size step it down one size, and a role with no measured peak never counts. The run API lists every attempt with its size, failure class, event-log state and next step, and the console's Maintenance tab shows them.

### Volcano queues and priorities

Maintenance SparkApplications are scheduled by Volcano. The `volcano` block in `chart/values.yaml` creates two Volcano queues and four PriorityClasses (`chart/templates/volcano.yaml`, wave 10 installs the CRDs) and renders their names for the worker as `GLAC_SPARK__VOLCANO__QUEUE`, `GLAC_SPARK__VOLCANO__URGENT_QUEUE` and `GLAC_SPARK__VOLCANO__PRIORITY_CLASS_PREFIX`:

| Table priority | Queue | PriorityClass | Value |
|---|---|---|---|
| P0 | `table-maintenance-urgent` | `table-maintenance-p0` | 1000003 |
| P1 | `table-maintenance` | `table-maintenance-p1` | 1000002 |
| P2 | `table-maintenance` | `table-maintenance-p2` | 1000001 |
| P3 (default) | `table-maintenance` | `table-maintenance-p3` | 1000000 |

Each queue's `capability` is one L job (`cpu: "2"`, `memory: 5017Mi`), with no `guarantee` and no `reclaimable`. Every class has `preemptionPolicy: Never` and `globalDefault: false`: a higher priority is picked first when capacity frees up, but never evicts a running job.

### Compaction candidates

A scheduled compaction picks partitions, not the whole table. Each scheduled reconcile observes the table and keeps one **compaction candidate** for each partition that has enough small files to merge. A candidate gets a random `cc-` id when its partition is first found, and keeps it while the partition stays a candidate. A candidate records its partition, its label (for example `ordered_at_day=2026-11-09`), what compacting it is worth (the files it removes), what it costs (the estimated GB-hours), its score and its state:

| State | Meaning |
|---|---|
| `pending` | Waiting to be picked. Its `rank` is its place among the pending candidates, best first. |
| `granted` | Picked by a compaction round (named by `granted_round_id`) for the table's next run. The grant has a lease of `grantLeaseSeconds`; one the table did not claim by then is pending again at the next observation, and the API lists it as pending as soon as the lease ends. An observation that holds a granted candidate with a filter (`too_small`, `recently_written`) ends its grant; `cooldown` and `not_due` keep it until its lease ends, and no hold ends a claim. |
| `held` | Kept out for now. `too_small` means it has less data than `minPartitionBytes`. `recently_written` means a writer added a file within `quietSeconds`; it is released once the writes pause, and after `maxQuietWaitSeconds` in a row at the latest. `cooldown` means the table's compaction is waiting out its cooldown, and `not_due` that it cannot run now for any other reason (trigger not met, needs attention, disabled or dry run); no round grants either. A `cooldown` hold keeps the time the candidate started to wait, since the cooldown is the table's own wait, so its SLA clock runs on; every other hold ends the wait. |
| `claimed` | Taken by a run (named by `claimed_by_run_id`) from its grant that has not started compacting yet. The claim has a lease of one operation's worst case plus one hour, so a run that never reports cannot keep it. |
| `running` | Its run is compacting it. |
| `done` / `failed` | Its run finished. The next observation removes it, or makes it `pending` again if it still has small files to merge. |

**Score.** The benefit is `min(1, files removed / benefitReferenceFiles)` and the cost is `min(1, GB-hours / costReferenceGbHours)`. The score is `(benefitWeight × benefit + costWeight × (1 − cost)) / (benefitWeight + costWeight)`, from 0 to 1. It uses fixed reference values, never the spread within one table, so the same score means the same on every table. The GB-hours come from the partition's bytes, the throughput measured from the table's past compactions of at least `minThroughputSampleBytes` (`defaultThroughputBytesPerHour` before it has any) and the memory of the size the table's compaction last succeeded at (S before it has succeeded). That is not always the size the run starts at: the start size depends on which partitions are picked, and the pick depends on the scores, so the remembered size is used to avoid a loop. Ties go to more files removed, then to the partition key.

**Compaction rounds.** One global round every `roundSeconds` decides which pending candidates, across every table, may be compacted. Each candidate carries the priority of its table's maintenance policy (`P0`, `P1` or `P2`, default `P2`). The round ranks the pending candidates by score × the weight of their priority and walks the ranking in order: it grants each one while the round's GB-hour budget lasts, and stops at the first one that does not fit, so every candidate after it waits (`budget_used`) even a smaller one. The first candidate is always granted, so a partition larger than the budget still gets its turn. A table's candidates past `partitionsPerRun` in one round wait too (`table_share_used`). A table busy with compaction gets nothing: one with a live granted, claimed or running candidate, or a done or failed one the next observation has not seen yet. Its pending candidates are not ranked; the round only counts them (`busy_skipped`), so they never take the place of a budget skip among the kept ones. Before it ranks, a round deletes the candidates of every table maintenance no longer manages (unmanaged, dropped or no longer known), whose reconciliation has stopped and will never observe them again. The round then signals each granted table, whose reconciliation plans at once. A candidate that has waited (pending or granted) longer than its priority's SLA is marked overdue; the SLA does not change the order. A round is recorded with its budget, the GB-hours it used, its picks and the first 20 skipped candidates with their reason; the newest `roundsKept` are kept. A round retried after its grants were saved rebuilds its record from them rather than granting a second set. A round that runs longer than three rounds, or than its activities can take with every retry plus a minute (14.5 minutes) when that is longer, is ended by Temporal, so the next one starts. The worker checks at start that the namespace has every search attribute it sets (`TableUuid`, `TableName`, `MaintenanceTrigger`, `MaintenanceOperations`, `GrantedTableUuids`) and refuses to start, naming `platform/21-temporal/bootstrap.sh`, when one is missing.

**Top N.** A scheduled run claims the `partitionsPerRun` best granted candidates and compacts only those. Pending candidates without a grant make the reconciliation record read `awaiting_schedule`. Its `rewrite_data_files` gets a where filter naming them, and it starts at least at the size that fits their bytes. A run that is retried keeps the candidates it claimed. When every partition is held, the reconciliation record reads `all_held` and the workflow looks again when the first hold ends. When every partition is claimed by another run, it reads `all_claimed`. A run that stops before it starts gives its candidates back. If an attempt runs out of memory, the next attempt compacts the best half of the picked partitions, then the best quarter, before the size goes up. A manual run compacts the whole table and leaves the candidates alone.

`GET /v1/tables/{uuid}/compaction-candidates` lists the candidates best first, with `partitions_per_run`, each with its priority, the round that granted it and when that round started, when it started to wait and whether it is overdue. The console's Candidates tab shows them, and says for each one why it is not in the next run. `GET /v1/compaction-rounds` (newest first, `limit`, `before`) and `GET /v1/compaction-rounds/{round_id}` return the rounds, each pick and skip naming its table by catalog, namespace parts and name; `GET /v1/scheduler-settings` returns the round interval, budget, grant lease and each priority's weight and SLA. `GET /v1/platform-settings` returns the platform's read-only settings in five groups (execution capacity, Spark sizes, compaction scheduling, cooldown and backoff, discovery), each a key, label, value, unit and one-sentence description built from a whitelist, so no secret can reach it; the console's Platform settings page (last in the nav) shows them. Two of them are the limits `worker.maxAttempts` (attempts per operation, default 3) and `worker.failureBackoffCapSeconds` (the longest wait after repeated failures, default 86400 s), which the ConfigMap gives to api and worker alike. The console's Compaction rounds page lists the newest 50, named by start time, and expands each into its picks and skips (`/compaction-rounds?round=<round id>` opens one); a priority reads with its SLA, for example `P2 (within 8 h)`.

The `compaction` block in `chart/values.yaml` sets these values. Each value is rendered as `GLAC_COMPACTION__<NAME>`, for example `GLAC_COMPACTION__PARTITIONS_PER_RUN`.

| Value | Default | Meaning |
|---|---|---|
| `partitionsPerRun` | `10` | A run compacts at most this many partitions, the best pending ones. |
| `minPartitionBytes` | `0` | A partition with less data is held as too small. With `0`, only "not enough files to merge" keeps a partition out. |
| `quietSeconds` | `120` | A partition written within this time is held as still being written. 120 s is two Iceberg sink commit intervals. |
| `maxQuietWaitSeconds` | `3600` | A partition is never held as still being written for longer than this in a row, so one written without pause is still compacted. |
| `benefitWeight`, `costWeight` | `0.7`, `0.3` | How much the files a compaction removes and its estimated cost count in the score. The weights are relative: the score is divided by their sum, so it stays between 0 and 1 whatever they add up to. |
| `benefitReferenceFiles` | `100` | Removing this many files scores the full benefit. |
| `costReferenceGbHours` | `1.0` | This many estimated GB-hours score the full cost. |
| `defaultThroughputBytesPerHour` | `2147483648` | The bytes per hour a compaction is assumed to rewrite before the table has finished runs to measure from. |
| `minThroughputSampleBytes` | `67108864` | A past compaction that rewrote less than this (64 MiB) does not count toward the measured throughput: its time is mostly Spark start-up and jar downloads. |
| `sizeSMaxBytes`, `sizeMMaxBytes` | `268435456`, `1073741824` | A run starts at least at S up to this much picked data, M up to the next, and L above. |

The api and worker read the same values: the worker picks with them, and the api shows the same top N in the console's Candidates tab. A value the selection refuses (an S bound above the M bound, both weights 0) stops the component at startup.

The `scheduler` block in `chart/values.yaml` sets the rounds. Each value is rendered as `GLAC_SCHEDULER__<NAME>`, for example `GLAC_SCHEDULER__BUDGET_GB_HOURS` and `GLAC_SCHEDULER__PRIORITY_WEIGHTS__P0`.

| Value | Default | Meaning |
|---|---|---|
| `roundSeconds` | `120` | A round runs this often (schedule `compaction-rounds`; a round still running when the next is due skips it, and one running longer than three rounds, or 14.5 minutes when that is longer, is ended). |
| `budgetGbHours` | `0.05` | The estimated GB-hours one round may grant. |
| `priorityWeights` | `P0: 4.0`, `P1: 2.0`, `P2: 1.0` | A candidate's score is multiplied by its priority's weight to rank it. |
| `slaSeconds` | `P0: 3600`, `P1: 14400`, `P2: 28800` | A candidate waiting longer than its priority's value is overdue. |
| `grantLeaseSeconds` | `600` | How long a grant waits for its table to claim it. |
| `roundsKept` | `500` | How many of the newest rounds are kept; older ones are deleted when a round is recorded. |

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryWorkflow` | schedule `table-discovery:catalog={catalog}` (Temporal appends the firing time); ad hoc `table-discovery:catalog={catalog}[:namespace={namespace}]:trigger=adhoc` | `{catalog}`; ad hoc `{catalog}[.{namespace}] · ad hoc` |
| `TableReconciliationWorkflow` | `table-reconciliation:table-uuid={uuid}` | `{catalog}.{namespace}.{table}` at first start |
| `TableMaintenanceWorkflow` | `table-maintenance:table={catalog}.{namespace}.{table}:run={run_id}` (table name as of the run start; stored on the run as `execution_ref`) | `{catalog}.{namespace}.{table} · {operations}` |
| `TableMaintenanceAdmissionWorkflow` | `table-maintenance-admission` | `global Spark maintenance admission (limit={limit})` |
| `CompactionRoundWorkflow` | schedule `compaction-rounds` (Temporal appends the firing time to the workflow ID; the workflow mints a `cr-` round ID once, which every retry of the schedule activity `schedule_compaction_round` reuses) | `compaction round · budget {budget} GB·h`; its current details read `round {cr-id} · granted {n} partitions of {m} tables`, and the search attribute `GrantedTableUuids` lists the tables it granted |

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
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`; runs whole-table, ignores cooldowns |
| `GET /tables/{uuid}/table-maintenance-runs`, `GET /table-maintenance-runs/{run_id}` | run history with per-operation status and metrics |

Save the rule list (read `version` with `GET /v1/discovery-rules` first; the list replaces the old one, so send the existing rules too):

```
curl -X PUT http://localhost:8000/v1/discovery-rules -H 'Content-Type: application/json' \
  -d '{"version": 0, "rules": [{"priority": 10, "action": "include", "enabled": true,
       "catalogs": ["iceberg"], "namespaces": ["e2e"], "tables": ["tm_e2e_*"]}]}'
```

A policy holds, per operation (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`), an `enabled` switch, a `trigger_policy` (`cooldown_seconds` and `conditions`) and an `execution_policy`; `rewrite_data_files` also has `scope.unit` (`partition` or `table`). `reconcile_interval_seconds` and `dry_run` sit at the top level. Read `GET /v1/maintenance-policies/default` for a complete body, and drop the fields the server sets (`id`, `name`, `is_default`, `version`, `created_at`, `updated_at`) before sending it as a new policy with its own `name` (for an update, send `version` back instead); unknown keys return 422.

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
5. already before the inserts (right after `CREATE TABLE`), creates the policies `tm-e2e-orders` and `tm-e2e-regions` as copies of `default` (updated if they exist) and attaches them to their tables; `tm-e2e-orders` has all four operations disabled, so it is inert for scheduling and carries only the execution values the manual run uses (`expire_snapshots` `older_than_seconds: 60`, `retain_last: 1`, `remove_orphan_files` `older_than_seconds: 86400`), and `tm-e2e-regions` stays schedulable (`scope.unit: partition`, `reducible_files.at_least: 2`, `cooldown_seconds: 60`, `reconcile_interval_seconds: 300`);
6. checks `GET /v1/tables/{uuid}/applicable-policy` of both tables, triggers all four operations on orders manually (a manual run plans every named operation whether or not it is enabled), and lets the regions scheduled plan compact through a `where` filter that contains the escaped quote;
7. requires every operation of the new runs to be `succeeded` with `rewritten_data_files_count > 0`, the orders data file count (`$files`) and snapshot count (`$snapshots`) to decrease, `expire_snapshots` to delete files and the RustFS object count under the orders `data/` prefix (one-off `pgsty/mc` pod) to be at most before + files added by the rewrite − files expired (the raw count can grow, because `older_than` is fixed at plan time and the rewrite's partial-progress commits still reference the old files), the regions file count to decrease, the regions `where` filter to contain `'o\'neil'` (read from the history of the run's maintenance workflow, whose ID the API returns as `execution_ref`), and both `table-reconciliation:table-uuid={uuid}` workflows to be running;
8. reads the orders `metadata`, `commits?limit=1000`, `health` and `storage` through the API and requires `total_data_files + total_delete_files` to equal the `$files` count (Trino's `$files` lists data and delete files), `snapshot_count` to equal the `$snapshots` count, the commits to be newest first, `health` to report four operations and `storage.reclaimed.rewritten_data_files` to be at least 20 (skipped when the compaction callback was lost).

If a Spark driver cannot deliver its result callback (the API or its database is down), the polling fallback records the operation as `succeeded` with `{"completed_without_callback": 1}` and no procedure metrics; the check then relies on the `$files` count alone and says so. Only `[INFO]` progress lines are printed; on failure the full output is dumped. The script is idempotent: it reuses the tables, the rule and the policies, so a rerun adds new small files. `remove_orphan_files` keeps files younger than one day, so it succeeds without deleting the files just written.

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
