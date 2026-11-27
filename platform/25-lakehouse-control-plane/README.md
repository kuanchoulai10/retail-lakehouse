# Lakehouse Control Plane

Wave 25. Creates the `lakehouse-control-plane` and `lakehouse-maintenance-operations` namespaces and deploys the table maintenance control plane as the Helm release `table-maintenance` (`chart/`). Its PostgreSQL is the wave before, `20-table-maintenance-db`; the chart only connects to it.

## Deployed Resources

```
Namespace: lakehouse-control-plane
  Job        table-maintenance-migrate-<rev>  creates the schema, seeds the "default" maintenance and discovery policies
  Deployment table-maintenance-api            Service table-maintenance-api:8000
  Deployment table-maintenance-worker         Temporal worker (task queue table-maintenance)
  Deployment table-maintenance-event-consumer Polaris catalog events from Kafka (1 replica)
  Deployment table-maintenance-console        data platform console (nginx), Service table-maintenance-console:8080
  HTTPRoute  table-maintenance-console        /console on platform-gateway (istio-ingress)
  Pod        table-maintenance-test-connection  helm test hook: calls the API's /healthz, deleted once it passes
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
2. copies the Polaris root credential (`polaris-bootstrap-secret`, as `client_id:client_secret`) into Secret `table-maintenance-polaris-credential`, and the RustFS credentials into Secret `table-maintenance-s3`, in both namespaces;
3. runs `build.sh`, which builds `table-maintenance-backend`, `table-maintenance-spark` and `console` (`src/data-platform/frontend`), tags them with the short git SHA of the last commit touching their source (`-dirty` when uncommitted) and loads them into minikube;
4. runs `helm upgrade --install table-maintenance ./chart --values values/minikube.yaml --wait`, setting only the three image tags; the S3 region it gave the Secret is read from that same file.

The Secret `table-maintenance-db` and the database come from `20-table-maintenance-db`, which `tasks/apps.yml` validates first. `validate.sh` ends its rollout checks with `helm test table-maintenance` (timeout `HELM_TEST_TIMEOUT`, default `120s`, apart from `TIMEOUT` because `tasks/apps.yml` runs `validate.sh` as a 10-second status check).

The Spark operator (wave 11) must watch `lakehouse-maintenance-operations` (`spark.jobNamespaces`).

## Console

The console is a static app served by nginx at `/console/`; nginx proxies `/console/api/` to this release's API, so the browser talks to one origin. The chart passes the API's address (`<release API name>.<namespace>.svc.cluster.local:<api.port>`) in `CONSOLE_API_UPSTREAM`, and the nginx image writes it into the server block at start-up; nginx resolves the name then; the chart always deploys the API with it. The `table-maintenance-console` HTTPRoute attaches to `platform-gateway` (wave `12-platform-gateway`) with path prefix `/console`; `bootstrap.sh` labels `lakehouse-control-plane` with `gateway::allow_routes` so the Gateway admits it. nginx redirects `/console` to `/console/` with a relative `Location` (`absolute_redirect off`), so the redirect keeps whatever scheme and port the browser used.

```
kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse
open http://localhost:8591/console/
```

`validate.sh` waits for the `table-maintenance-console` rollout and the route's `Accepted` condition, then curls the gateway (`gateway::curl`) and checks that `/console`, `/console/` and the deep link `/console/tables/x/commits` return the app and `/console/api/v1/tables` returns a JSON array.

## Ordering

The `migrate` Job is a regular Job named with the Helm release revision, so each upgrade runs it again. The Job waits for `pg_isready` on the host and port of `external.database.postgresql.endpoint`, as the Secret's `username`. The api, worker and event-consumer pods have an init container that waits until the `default` maintenance policy exists, which means the migration finished (there is no default discovery policy).

## Chart values

The chart follows the conventions of open-source charts such as Trino's (`trinodb/charts`), Sentry's and Bitnami's. **Its `values.yaml` holds every generic setting with its value filled in and leaves every environment value empty, so the chart deploys to any cluster that has the six external services once an environment file names them.** Without one the chart refuses to render, naming the first value it misses. This cluster's environment is `values/minikube.yaml`; `values/e2e.yaml` only shortens the waits the e2e sits through.

| Block | What it sets |
|---|---|
| `nameOverride`, `fullnameOverride`, `commonLabels`, `imagePullSecrets`, `extraManifests` | every object's name (`<release>-table-maintenance-<role>`, or `<release>-<role>` when the release name already holds the chart name), labels on every object, and further manifests rendered with templating |
| `global` | `image.registry`, `image.pullPolicy`, and the `env`, `envFrom` and `secretMounts` every pod gets (merged by name: a global entry replaces one of the chart's own, a role's entry replaces both, and each name appears once) |
| `external` | the services the chart connects to and does not run, each with a `type` that accepts one value: `database` (`postgresql`: `endpoint`, `database`, `credentialsSecret`, `sslMode`, `poolSize`), `orchestrator` (`temporal`: `endpoint`, `namespace`), `catalog` (`polaris`: `endpoint`, `scope`, `credentialsSecret`; the chart adds `/api/catalog` and `/api/management/v1`), `objectStorage` (`s3`: `endpoint`, `region`, `pathStyleAccess`, `credentialsSecret`), `catalogEvents` (`kafka`: `endpoint`, `topic`) and `metricsHistory` (`prometheus`: `endpoint`, `queryTimeoutSeconds`) |
| `backend` | `image`, `logLevel`, and one block per role, `api`, `worker`, `eventConsumer`, `migrate`: `replicas` (not `migrate`), its own `logLevel` (empty means `backend.logLevel`), `labels` / `annotations`, `podLabels` / `podAnnotations`, `nodeSelector`, `tolerations`, `affinity`, `resources`, `env`, `envFrom`, `secretMounts`; `api` adds `port` (where the API listens, written to its `http.port`), `rootPath`, `httpRoute.gateway`, `readinessProbe` and `livenessProbe` (`path` and the timings) and `connectionTest.resources` (the `helm test` pod), `worker` its `terminationGracePeriodSeconds`, `serviceAccount` and `rbac`, `eventConsumer` its `terminationGracePeriodSeconds`, `migrate` `backoffLimit` and `waitForDatabase.image` and `.resources` (the schema wait in front of every service takes `migrate.resources`) |
| `frontend` | `image` and the `console` block (the role keys above plus `port`, where nginx listens through `CONSOLE_PORT`, `httpRoute.gateway`, `readinessProbe` and `livenessProbe`) |
| `maintenance` | `discovery`, `cooldowns`, `failureBackoffCapSeconds`, `partitionSelection`, and `jobs`: the Spark `image`, `namespace`, `serviceAccount`, `rbac`, `limits`, `sizes` S / M / L, `cores`, `spark` versions and paths, and `scheduling` (the Volcano queues and PriorityClasses) |

**An endpoint is a URL for an HTTP service and `host:port` for the others** (Kafka takes a comma-separated list), and each `credentialsSecret` names a Secret with fixed keys: the database's `username` and `password`, Polaris's `credential` (`client_id:client_secret`), S3's `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

**Every role always deploys; there is no `enabled` switch.** The `create` switches that remain hand an object to someone else: `backend.worker.serviceAccount.create: false` and `maintenance.jobs.serviceAccount.create: false` need the existing `name`, and `maintenance.jobs.scheduling.create: false` needs both queue names and `priorityClassPrefix`. `backend.worker.rbac.create: false` and `maintenance.jobs.rbac.create: false` render no Role or RoleBinding, and whoever owns them grants the worker `create`, `get`, `list`, `watch` and `delete` on `sparkapplications` and `get` and `list` on `pods` in the jobs namespace, and the Spark ServiceAccount what the Spark driver needs there (pods, services, configmaps and persistent volume claims, and events).

**An environment value left out or a contradiction fails before install, with the value to change:** every external `endpoint` and `credentialsSecret`, the database name, the Temporal namespace, the S3 region, the Kafka topic, both Gateways' name and namespace, `maintenance.jobs.namespace` and `maintenance.jobs.spark.eventLogDir`; a `create: false` without its names; and a `GLAC_MAINTENANCE__`, `GLAC_DISCOVERY__` or `GLAC_SPARK__` variable in one role's `env`, since those settings are shared. `values.schema.json` refuses a key the chart does not know (`backend.worker.replica`, any `enabled`), a value of the wrong type or shape (an image tag that is a number, an endpoint of the wrong form, an unknown log level or SSL mode), a `replicas` below 1, an `eventConsumer.replicas` other than 1, and a label key under `app.kubernetes.io/` or `helm.sh/` in `commonLabels`, `labels` or `podLabels`, since the chart sets those itself; each error names the key.

## Chart tests

The chart is checked three ways, each aimed at a different mistake, and none needs a cluster.

**helm-unittest checks the template logic and that every value reaches the field it sets.** `task -d platform/25-lakehouse-control-plane unit-test` runs the suites in `chart/tests/`, `helm lint` and a render of each scenario in `chart/ci/` (each a whole environment: a plain one, a renamed release, and one in another cluster where RBAC, Volcano and the ServiceAccounts belong to someone else, with every pass-through set and other ports), and `helm lint` of `values/minikube.yaml` alone and with `values/e2e.yaml`. `wiring_test.yaml` sets a value off its default and checks it lands in every object that uses it, and `schema_constraints_test.yaml` breaks each rule of `values.schema.json` once and checks the error names the key. There are no snapshot tests: a snapshot fails on any change and cannot say which behaviour mattered. helm-unittest is a Helm plugin pinned at `1.2.1`; the task stops with the install steps when it is missing, and the install verifies the release's signature against the project's `public-key.asc`.

**`scripts/check_chart_manifests.py` checks what every render keeps, whatever the values.** `task -d platform/25-lakehouse-control-plane security-test`, which the pre-pr gate runs on its backend side, renders each scenario and runs kubeconform `v0.8.0` (strict and offline, against the Kubernetes `v1.33.2` schemas in `schemas/kubernetes-v1.33.2/` and the HTTPRoute and Volcano Queue schemas in `schemas/crds/`), the label standard of `scripts/check_k8s_labels.py`, and the deployment rules the script's docstring lists: pods that run as non-root under seccomp `RuntimeDefault`, containers that drop every capability and request their resources, no API token without a ServiceAccount of its own, probes on declared ports, Services that target named ports of the pods they select, routes that never take the whole Gateway, the settings checksum on every pod that mounts its settings, Jobs that end, the event consumer replaced with `Recreate`, PriorityClasses that never preempt and are never the cluster default, and the Spark driver's Role. After an upgrade of Gateway API (wave 11) or Volcano (wave 10), `task -d platform/25-lakehouse-control-plane schemas KUBE_CONTEXT=retail-lakehouse` rewrites the CRD schemas from wave 11's vendored CRD and the cluster's Volcano CRD (`scripts/crd_json_schemas.py`); after a Kubernetes upgrade, fetch that version's `*-standalone-strict` files for the kinds the chart renders from `yannh/kubernetes-json-schema`.

**Drift tests keep the chart's defaults on what the components do.** In the backend, `tests/bootstrap/configs/test_chart_settings.py` checks that each role starts with the file the chart writes for it, that every setting a role reads has a key there and that every generic value equals the backend's default, and `tests/bootstrap/container/test_chart_probes.py` that the API answers the paths the chart probes. `scripts/tests/test_console_chart_drift.py` checks that the console image listens on the port the chart gives it and that the route prefix and the probes use the path the console is built for.

**`task -d platform/25-lakehouse-control-plane mutation-test` checks the checks.** `scripts/mutate_chart.py`, run by `nightly`, breaks the templates and the schema one way at a time and runs the unit tests and the manifest checks on each mutant, listing every mutant both miss; it refuses to start when they fail on the unbroken chart. A mutant no render can tell apart goes in `chart/mutation-ignore.yaml` with its reason (five today: release-name truncation, which Helm's 53-character limit makes unreachable, the `PathPrefix` that Gateway API defaults to, and the event consumer's `replicas`, which the schema pins to Kubernetes' default). On 2026-11-26 it killed 931 of 931. On the cluster, `validate.sh` runs `helm test`.

## Configuration

**Each backend role reads its own settings file** (ADR 0017). The chart renders one ConfigMap per role, `table-maintenance-{api,worker,event-consumer,migrate}-config`, holding `config.yaml`, mounts it at `/etc/glac` and runs `glac <role> --config-file=/etc/glac/config.yaml`. **The chart writes every setting a role reads, from the values, cut to the keys the role takes:** the generic values carry the backend's defaults (a backend test keeps the two equal), the environment values come from the environment file, and the chart's own wiring (the Spark image, ServiceAccount, Volcano names, callback URL and route prefix) follows the release. Each Deployment's `checksum/config` covers its own file, so a change restarts only the roles that read it. The backend refuses to start on a file key or `GLAC_*` variable its role does not take, naming it.

Only secrets are environment variables: `DB_USERNAME` and `DB_PASSWORD` from the database Secret, which build `GLAC_DATABASE__POSTGRES__DB_URL` (`postgresql+psycopg://$(DB_USERNAME):$(DB_PASSWORD)@<endpoint>/<database>?sslmode=<sslMode>`), and `GLAC_CATALOG__CREDENTIAL` from the Polaris Secret; the API and the worker load the S3 Secret whole, for the event logs. The services' init container runs `glac migrate --wait`, which waits until the migrate Job has migrated and seeded the schema. **No setting names the catalogs to scan: the scanned catalogs follow where discovery policies are attached.** A catalog is scanned while a discovery policy is attached to it, or to a namespace or table in it, whatever its rules, and while it still holds managed tables; `maintenance.discovery.intervalSeconds` only sets how often the one `table-discovery` schedule starts a round over every scanned catalog.

### Spark sizes

Every maintenance attempt runs at one of three sizes, set by `maintenance.jobs.sizes.<S|M|L>.{driverMemory,executorMemory,executorInstances}` and written as `spark.size_<s|m|l>.{driver_memory,executor_memory,executor_instances}` in the API's and the worker's settings files. Driver and executor stay capped at one core; memory overhead is Spark's default (`max(384Mi, 0.4 × memory)` for a Python application), so the pod requests are:

| Size | Driver memory | Executor memory | Executors | Pod requests, driver + executor |
|---|---|---|---|---|
| S | `768m` | `768m` | 1 | 1152Mi + 1152Mi = 2304Mi |
| M | `1g` | `1536m` | 1 | 1434Mi + 2150Mi = 3584Mi |
| L | `1536m` | `2g` | 1 | 2150Mi + 2867Mi = 5017Mi |

An L job fits on the 8-CPU / 26 GB node only alone; next to another Spark job it stays queued while its queue-wait clock runs (its attempt deadline starts only once its driver runs). A partial override (only `maintenance.jobs.sizes.L.executorMemory`) keeps the other values of that size.

An operation starts at the size its table last succeeded at (S for a table that never did). Each failed attempt is classified when it is recorded: `oom` (a driver or executor container `OOMKilled` or exit 137, an executor exit 52, or `java.lang.OutOfMemoryError` / `OOMKilled` / `exit code 52` in the error or a driver termination message; container exits count only when Spark itself ended the attempt, since the platform's own deletes also exit 137), `timeout`, `queue_timeout`, `commit_conflict`, `permanent` (missing table, forbidden), `cancelled` or `other`. An attempt's deadline and queue wait are timed apart (see Queue wait and run time); one stopped in the queue is not retried. An `oom` retries at the next size; `permanent` is not retried; other failures retry at the same size, within `maintenance.max_attempts` (3) attempts. An `oom` at L stops the operation and marks it **needs attention** on the table: reconcile stops planning it until a manual run of it, or until another policy (or policy version, or the same policy attached elsewhere) applies to the table than the one its run was planned under. The next reconcile after such a change clears the mark for good, so going back to the earlier policy does not bring the block back; until that reconcile, the table API still shows the mark. A success records the attempt's size, and the Spark runtime reports the peak heap the driver and the busiest executor used, in bytes (reported as `peak_coordinator_memory_bytes` and `peak_worker_memory_bytes`, read from the driver's own Spark UI REST API on localhost before the session stops). A success counts toward stepping down only when both peaks fit within 70% of the next smaller size's driver and executor memory (as set in `maintenance.jobs.sizes`); three such successes in a row at the remembered size step it down one size, and a role with no measured peak never counts. The run API lists every attempt with its size, failure class, event-log state and next step, and the console's Maintenance tab shows them.

### Volcano queues and priorities

Maintenance SparkApplications are scheduled by Volcano. The `maintenance.jobs.scheduling` block in `chart/values.yaml` creates two Volcano queues and four PriorityClasses (`chart/templates/volcano.yaml`, wave 10 installs the CRDs) and writes their names for the worker as `spark.volcano.queue`, `spark.volcano.urgent_queue` and `spark.volcano.priority_class_prefix`:

| Table priority | Queue | PriorityClass | Value |
|---|---|---|---|
| P0 | `table-maintenance-urgent` | `table-maintenance-p0` | 1000003 |
| P1 | `table-maintenance` | `table-maintenance-p1` | 1000002 |
| P2 | `table-maintenance` | `table-maintenance-p2` | 1000001 |
| P3 (default) | `table-maintenance` | `table-maintenance-p3` | 1000000 |

Each queue's `capability` is one L job (`cpu: "2"`, `memory: 5017Mi`), with no `guarantee` and no `reclaimable`. Every size requests 2 CPU and the cap is cpu 2, so each queue runs one job of any size at a time; the cpu cap is what to raise for more concurrency (the memory cap then decides how many fit). Every class has `preemptionPolicy: Never` and `globalDefault: false`: a higher priority is picked first when capacity frees up, but never evicts a running job. The backend sets the class on the PodGroup only, not on the driver and executor pods: the class orders the queue, and pods without one are evicted under node memory pressure no later than platform services, which have none either.

### Queue wait and run time

A maintenance attempt spends its time in two places, waiting in its Volcano queue and then running, and the two are timed apart so a long queue never makes a healthy job time out. An attempt is `queued` from its submit until its Spark driver container starts, which the worker reads from the driver pod on each status poll (`state.running.startedAt`, else `state.terminated.startedAt`, else `lastState.terminated.startedAt`). From that start its deadline, `maintenance.attempt_deadline_seconds` (21600), runs. The attempt records both times, `started_at` (the submit) and `started_running_at` (the driver start, clamped between the submit and the poll that read it), and the console's Maintenance tab shows how long it queued and how long it ran; a duration of an hour or more shows in hours. If the driver pods cannot be read, the attempt cannot see its driver start: at the queue wait limit a job still pending ends `queue_timed_out`, and one running or completed is taken as started at that poll (each failed read is logged as an error).

The wait in the queue has a limit of its own, `maintenance.queue_wait_limit_seconds` (86400). At the limit the worker polls the attempt once more: if that poll reads its driver start, the attempt runs on under its deadline from that start; a job that reads running or completed but whose driver start cannot be read is taken as started at that poll, so a completed one gets its callback grace and a running one its deadline from then; and a job that failed or went missing ends as any poll would. Only an attempt whose job is still pending with no driver start (or whose status cannot be read) is stopped (its Spark job is deleted and its pods are polled until none is live), ends `queue_timed_out` with failure class `queue_timeout`, and is not retried: its operation waits for the next plan. The worker polls a queued attempt every 30 s for the first 10 minutes and then every 10 minutes, and a running one every 30 s for the first 10 minutes after its driver starts and then every 5 minutes, which keeps the workflow history small. **A driver start is therefore seen up to one poll interval late** (the attempt still records the driver's own start time); the poll at the limit is what keeps a driver that started within the last interval from being stopped. The reconciliation's give-up bound for a run that never reports counts every attempt's queue wait limit as well as its deadline.

A manual run on a table whose run is in flight does not start a second one: it raises the priority of the runs in flight, the one running and the ones still pending, only upward (`P0` over `P1` over `P2` over `P3`), and a manual run with no priority means the table's current one. A lower or equal priority changes nothing. The run that is running is not interrupted, and the runs after it are submitted at the new priority. An attempt that is still `queued` is replaced only when its job reads `PENDING` with no driver start: its job is deleted and submitted again at the new priority under the same attempt number, which does not count toward `maintenance.max_attempts` and keeps the attempt's submit time and queue deadline. A job the Spark operator is still submitting (no application state yet) reads `SUBMITTING` and is not replaced: the spark-submit under way would create a driver under the shared name after the old job is gone, and the replacement's own submit would fail on it. The raise stays wanted and the job is read again 5 s later within the first 10 minutes of its submit, at the queued pace (10 minutes) after. Every job delete (a requeue, a fence, the end of a run) uses foreground propagation: the SparkApplication stays readable, marked for deletion, until the pods and PodGroup it owns are gone, so the replacement is submitted only once the old job reads `NOT_FOUND` and has no live pods, and never meets the old PodGroup. The same holds between runs: the next run submits only after the previous run's Spark jobs are gone, and the workflow reports to the reconciliation only after the last run's jobs are gone. A driver that starts between the check and the delete is killed with the job, and the attempt runs again, which the maintenance procedures allow; a result that killed job sends meanwhile is dropped, so only the replacement's result counts. A running attempt, and one whose driver has started, is left alone. The manual trigger is consumed once the raise is delivered. The run reports, when it ends, whether it left a raise unapplied (one that arrived after its last attempt ended, or whose record failed) and how many raises it had received; the reconciliation gives the manual trigger back, to be planned as a run of its own after this one, when the run left a raise unapplied or received fewer raises than were delivered to it (a raise that reached it after it built its report). The trigger is dropped instead when the plan that would run it fails, the table is skipped, nothing is planned, or the workflow is stopping. A run whose workflow closed without reporting is treated as finished and gives its trigger back: at once when the reconciliation execution that started it sees the close (a run already closed is never carried through continue-as-new); a run carried through continue-as-new when a raise cannot reach it and a lookup finds its workflow no longer running, otherwise at the give-up bound. A run that is given up gives its trigger back too, whether or not it reports after the cancel, because the cancel stopped its work. After a run reports, the reconciliation waits for its workflow to close before it starts the next, at most the report activity's worst case, so the table's one workflow id is free; a start that is refused after that is recorded as `run_start_failed`. The runs of a plan are created, `pending`, by the reconciliation in one transaction before it starts the child, so a reconciliation never links a run that does not exist: when that create fails no child starts and the reconciliation records `run_start_failed` with no run, and when the child is refused its start the runs just created are skipped (`skip_reason` "the table's maintenance workflow could not be started"). Changing a table's own priority never touches a run in flight: it applies from the next plan.

`GET /v1/platform-settings` returns the platform's read-only settings in five groups (execution capacity, Spark sizes, cooldown and backoff, compaction partition selection, discovery), each a key, label, value, unit and one-sentence description built from a whitelist, so no secret can reach it; the console's Platform settings page (last in the nav) shows them. **The maintenance limits, cooldowns and back-off are set by the deployment, not by a policy:** they are set under `maintenance` for the API and the worker alike, and the chart refuses them in one role's `env`.

| Setting | Chart key | Default | Meaning |
|---|---|---|---|
| `maintenance_attempt_deadline_seconds` | `maintenance.jobs.limits.attemptDeadlineSeconds` | 21600 | How long one attempt may run, from its driver start |
| `maintenance_queue_wait_limit_seconds` | `maintenance.jobs.limits.queueWaitLimitSeconds` | 86400 | How long one attempt may wait in its Volcano queue |
| `maintenance_max_attempts` | `maintenance.jobs.limits.maxAttempts` | 3 | Attempts per operation |
| `maintenance_rewrite_data_files_cooldown_seconds` | `maintenance.cooldowns.rewriteDataFilesSeconds` | 3600 | The least time between two compactions of one table |
| `maintenance_rewrite_manifests_cooldown_seconds` | `maintenance.cooldowns.rewriteManifestsSeconds` | 21600 | The least time between two manifest rewrites of one table |
| `maintenance_expire_snapshots_cooldown_seconds` | `maintenance.cooldowns.expireSnapshotsSeconds` | 21600 | The least time between two snapshot expiries of one table |
| `maintenance_remove_orphan_files_interval_seconds` | `maintenance.cooldowns.removeOrphanFilesIntervalSeconds` | 604800 | How often orphan files are removed from a table whose policy holds the block |
| `maintenance_compaction_partitions_per_job` | `maintenance.partitionSelection.partitionsPerJob` | 10 | The most partitions one scheduled compaction rewrites; those over the target for the longest wait go first, oldest first, then the most reducible first |
| `maintenance_compaction_quiet_seconds` | `maintenance.partitionSelection.quietSeconds` | 120 | How long after its last write a partition waits before it is compacted; 0 never waits |
| `maintenance_compaction_max_quiet_wait_seconds` | `maintenance.partitionSelection.maxQuietWaitSeconds` | 3600 | How long a partition over the target may keep waiting for quiet before it is compacted anyway; a partition over the target this long also goes first under the per-job cap, oldest first; 0 means nothing waits |
| `maintenance_failure_backoff_cap_seconds` | `maintenance.failureBackoffCapSeconds` | 86400 | The longest wait after repeated failures; each consecutive failure doubles the operation's cooldown up to it |

## Temporal workflows

All run on task queue `table-maintenance` in Temporal namespace `default`. IDs are a name followed by `key=value` segments joined by `:`.

**One discovery schedule scans every catalog, one scan per catalog at a time.** The schedule `table-discovery` is ensured by the worker at every start, before it polls: it is created, or updated to the configured interval and unpaused, and a failure stops the start. It fires every `discovery.interval_seconds` (600 by default) with overlap `SKIP`. Each firing starts a round, which lists the scanned catalogs and starts one scan per catalog as a child it does not wait for, skipping a catalog whose scan is still running. A slow or unreadable catalog therefore never delays the others. A catalog is scanned while a discovery policy is attached to it, to one of its namespaces or to one of its tables, and while it still holds a managed table, so the scan after the last detach unmanages them. An attach, a detach or a policy save asks for a scan of the smallest place it touched (best effort: a failure is logged and the request still succeeds). A catalog request is a signal-with-start: it starts the catalog's scan, or tells the running one to scan once more when it finishes. A namespace request starts its own scan and sends the same signal to the running catalog scan.

| Workflow type | Workflow ID | Static summary |
|---|---|---|
| `TableDiscoveryRoundWorkflow` | `table-discovery:round`, started by the schedule `table-discovery` (Temporal appends the firing time) | `every scanned catalog` |
| `TableDiscoveryWorkflow` | a catalog's scan `table-discovery:catalog={catalog}`, the same id whether a round, an attach, a policy save or a catalog event starts it (signal `request_rescan` asks a running scan to scan once more, as a new run through continue-as-new); a namespace's scan after a discovery policy change `table-discovery:catalog={catalog}:namespace={namespace}:trigger=policy-changed:change={id}` (a fresh 32-hex id per change); any other namespace scan `table-discovery:catalog={catalog}:namespace={namespace}:trigger=adhoc` | `{catalog}` from a round; requested `{catalog}[.{namespace}] · ad hoc` |
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
| `GET, POST /discovery-policies`, `GET, PUT, DELETE /discovery-policies/{name}`, `GET /discovery-policies/{name}/versions/{version}` | versioned discovery policies, with no default among them; a policy is a `description` and ordered `rules`, at least one, each `{"action": "include" \| "exclude", "table_name_pattern": "<glob>"}` matched against the table name alone, the last matching rule deciding and no match meaning not managed (exclude rules alone are allowed); `PUT` carries the `version` it was edited from (409 when stale), and deleting a policy still attached anywhere returns 409 naming each place |
| `GET, PUT /discovery-policies/{name}/attachments`, `DELETE /discovery-policies/{name}/attachments?target_type=&path=…` | list the places a discovery policy is attached to (each `orphaned` once it left the catalog), attach it to a catalog, namespace or table (`{"target": {"type": "namespace", "path": ["iceberg", "e2e"]}}`, replacing what that place holds; a table discovery has not seen is recorded `undecided`), or detach it from a place (`path` repeated once per part; 404 when the place does not hold it; the catalog is not read, so an orphaned place detaches too); a table follows the nearest place holding a discovery policy (table, then namespaces deepest first, then catalog), which replaces its parents whole, and with none it is not managed; a place that does not exist is 404 (an empty catalog or namespace exists), a namespace level holding a `.` is 422, and a catalog the platform's credential cannot read is 403 |
| `GET /scanned-catalogs` | the catalogs discovery scans (a discovery policy is attached in it, or it still holds managed tables), by name, each with `last_discovered_at` and its current `failure` (`{reason, detail, failed_at}`, `reason` `cannot_access` or `not_found`, or null) |
| `GET, POST /maintenance-policies`, `GET, PUT, DELETE /maintenance-policies/{name}`, `GET /maintenance-policies/{name}/versions/{version}` | versioned maintenance policies; the migration seeds `default`; `PUT` carries the `version`, and deleting `default` or an attached policy returns 409 |
| `GET, PUT /maintenance-policies/{name}/attachments`, `DELETE /maintenance-policies/{name}/attachments?target_type=&path=…` | the same shape for maintenance policies: list the places (`orphaned` once gone), attach (`{"target": {"type": "table", "path": ["iceberg", "e2e", "tm_e2e_orders"]}}`) or detach from a place |
| `GET /tables/{uuid}/effective-policies`, `GET /effective-policies?catalog=&namespace=&table=` | the policy of each kind that applies after inheritance (table, then namespaces deepest first, then catalog, then the maintenance `default`), as `{"policies": [maintenance, discovery]}`; each entry names the policy (`policy_id`, `policy_name`, its latest `version`, `description`) and the `target` holding it (null for the maintenance default), the maintenance entry adds `dry_run`, and a discovery entry with no policy on the walk has every field but `kind` null; by uuid, a table maintenance has no record of is 404; by location (namespace dot-joined), a catalog, namespace or table the catalog does not hold is 404 and a catalog the platform cannot read is 403 |
| `GET /tables?status=managed` | tables (`managed`, `unmanaged`, `undecided`, `dropped`), each with `decided_by` (`{policy_id, policy_version, rule_position}` or null), `last_committed_at` (the newest snapshot's commit time) and `last_discovered_at` (when a catalog scan last saw it); both null when unknown |
| `GET /table-metrics` | the Prometheus exposition of every managed table's current metrics (17 gauge series per table, text format 0.0.4); hidden from the OpenAPI schema, since only the Prometheus of wave `26-table-metrics-prometheus` reads it, every 30 s |
| `GET /tables/{uuid}/metrics/current` | the table's latest saved metrics (files by content type, data size and records, delete records, reducible files, manifests and their entries, snapshots) and when the reconcile observed them; `observed_at` and `metrics` are null for a table not reconciled yet or not managed; 404 for an unknown table |
| `GET /tables/{uuid}/metrics?range=1h\|3h\|6h` | the same metrics over time, read from that Prometheus (default `6h`, one point per 30 s / 90 s / 180 s; a gap is `null`); 404 for an unknown table, 502 with the reason when Prometheus cannot answer. The URL comes from `metrics.prometheusUrl` in `chart/values.yaml` (`metrics.prometheus_url`) |
| `POST /tables/{uuid}/maintenance` | manual run, body `{"operations": [...]}`, optional `priority`; runs whole-table with the options of the applicable policy's blocks (an operation the policy leaves out runs with the platform's choices), ignores cooldowns; while a run is in flight it raises that run's priority instead of starting another |
| `GET /tables/{uuid}/table-maintenance-runs`, `GET /table-maintenance-runs/{run_id}` | run history, one run per operation, with what its job does (`settings`, and `partitions` for a compaction), procedure numbers (`metrics`) and attempts |
| `POST /table-maintenance-runs/{run_id}/result` | the callback a Spark job posts for one attempt of the run; the run names its operation, and a body that names another one is refused with 422 |
| `GET /tables/{uuid}/reconciliations`, `GET /table-reconciliations/{id}` | the table's reconciliation records, newest first, and one record by id; each started operation names the `run_id` of its run |

Create a discovery policy, then attach it; the attach makes the catalog scanned and starts a scan of the namespace:

```
curl -X POST http://localhost:8000/v1/discovery-policies -H 'Content-Type: application/json' \
  -d '{"name": "tm-e2e", "rules": [{"action": "include", "table_name_pattern": "tm_e2e_*"},
       {"action": "exclude", "table_name_pattern": "*_tmp"}]}'
curl -X PUT http://localhost:8000/v1/discovery-policies/tm-e2e/attachments -H 'Content-Type: application/json' \
  -d '{"target": {"type": "namespace", "path": ["iceberg", "e2e"]}}'
curl -X DELETE 'http://localhost:8000/v1/discovery-policies/tm-e2e/attachments?target_type=namespace&path=iceberg&path=e2e'
```

A policy describes the state a table is kept in. Its body has a `description`, `on`, `dry_run` and up to four operation blocks. `on.schedule.every_seconds` (60 to 604800) is how often the table is checked, and the optional `on.catalog_commit.debounce_seconds` (0 to 86400, default 300) checks the table a debounce after a commit; leave `catalog_commit` out and commits trigger nothing. Each operation (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`) is a block `{target, options}`; a block that is absent or `null` means the policy does not do that operation, and a policy may hold no block at all. Read `GET /v1/maintenance-policies/default` for a complete body, and drop the fields the server sets (`id`, `name`, `is_default`, `version`, `created_at`, `updated_at`) before sending it as a new policy with its own `name` (for an update, send `version` back instead); unknown keys return 422.

**`target` says when an operation is due, `options` only how it runs.** `target` is the state the table is kept in: `rewrite_data_files` holds `reducible_files.at_most` and `per` (`partition`, the default, or `table`), `rewrite_manifests` holds `small_manifests.at_most`, `expire_snapshots` holds `min_snapshots_to_keep` (at most 2147483647) and `max_snapshot_age_seconds` (at most 3153600000, 100 years), and `remove_orphan_files` holds `older_than_seconds` (86400 to 3153600000). An operation is due when the table is off its target, and the platform cooldown (see the settings above) holds it back after a run; orphan file removal has no cheap target, so its block alone makes it due on the platform interval. **A scheduled `per: partition` compaction rewrites only the partitions over the target.** A check picks at most `worker.compactionPartitionsPerJob` of them (10): first those that have been over the target for `worker.compactionMaxQuietWaitSeconds` (oldest first), then the rest, the most reducible files first. The run's `rewrite_data_files` passes one `where` clause per partition spec; the partitions it leaves out wait for the next check that `on:` and the rewrite cooldown allow, so a partition waits at most about the longest wait plus the checks the overdue partitions ahead of it need. A partition written within `worker.compactionQuietSeconds` (120) waits too, so a compaction does not collide with a writer; once a partition has been over the target for `worker.compactionMaxQuietWaitSeconds` (3600) it stops waiting. When every partition over the target waits, the check records the verdict and result `waiting_for_writes` with `next_eligible_at`, and starts nothing. `per: table` ignores the quiet period, and a manual run always compacts the whole table. `GET /v1/table-maintenance-runs/{id}` and the run lists carry `partitions` on each compaction run, the partitions it rewrites per spec (`[{spec_id, fields, partitions}]`, `[]` for the whole table). A retention value the policy leaves out is the table's `history.expire.*` property, else Iceberg's default; a table age property over 100 years (Iceberg's `Long.MAX` "never by age") is read as 100 years. `options` are the arguments the Iceberg procedure runs with, a curated subset of each procedure's (the runtime's `README.md` lists them); an option left out is the procedure's default, and a key the platform owns (`where`, the target file size, `older_than`, `retain_last`) is refused. `dry_run` makes scheduled checks record what would run and start nothing; a manual run still runs.

A table's reconciliation checks the table when its schedule fires; when a commit window closes (the first commit not yet checked opens a window of the debounce, later commits join it without moving its end, and any other check but a manual run takes it, since a manual run looks only at the operations it names); and always, whatever `on` says, for a manual run, Reconcile now, a policy change and a table becoming managed (a discovery scan only keeps the workflow alive).

## End-to-end check

The e2e is a pytest package, `src/data-platform/backend/e2e/`, that checks the deployed platform from outside: it imports none of the backend's code (import-linter contract `e2e-black-box`), talks to the API, Polaris, Temporal and RustFS as a client, and needs no query engine, so it runs with Trino stopped. It runs in the cluster as one pod, built from `table-maintenance-e2e`, an image on top of the production backend image that adds only pytest, `pyiceberg-core` and the scenarios (`e2e.Dockerfile`; the backend image's tag ignores `e2e/` and the e2e image files, so changing a scenario does not redeploy the platform).

```
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e/run.sh critical   # minutes
KUBE_CONTEXT=retail-lakehouse SETTINGS_PROFILE=e2e bash platform/25-lakehouse-control-plane/bootstrap.sh   # before full
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e/run.sh full       # about 45 minutes
KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh   # back to the default profile
```

**The full round needs the e2e settings profile, which waits less.** `bootstrap.sh` takes `SETTINGS_PROFILE=default|e2e` (default `default`; anything else stops it before any cluster call) and adds `values/e2e.yaml` over `values/minikube.yaml` for `e2e`, which sets four maintenance values, for the API and the worker: `partitionSelection.quietSeconds` 60 (120), `partitionSelection.maxQuietWaitSeconds` 180 (3600), `cooldowns.rewriteDataFilesSeconds` 60 (3600) and `jobs.limits.queueWaitLimitSeconds` 900 (86400). The profile is named in the deploy's last line. The e2e pod mounts the worker's settings file (`table-maintenance-worker-config`) and compares the platform settings page with what it sets; it takes the service addresses from its own `E2E_*` variables in `e2e/pod.yaml`, since it imports none of the backend's code. A scenario that waits out one of those calls `require_settings` first and fails in a second, naming the profile, on a platform deployed with the defaults; the others pass under either profile. `task gates:nightly:e2e-full-test KUBE_CONTEXT=…` deploys `e2e`, runs `full`, and deploys `default` back on every exit.

`task gates:nightly:e2e-full-test KUBE_CONTEXT=…` runs `full`, and `task gates:pre-merge:e2e-critical-test KUBE_CONTEXT=…` runs `critical` (without `KUBE_CONTEXT` it prints its `TODO://` for the ephemeral platform). `run.sh` builds the images (`build.sh`), starts the pod `table-maintenance-e2e-<8 hex>` in `lakehouse-control-plane` from `e2e/pod.yaml`, follows its log (attaching again when the stream drops while the scenarios run) and exits with the scenarios' exit code; the pod is deleted on every exit. It refuses to start while another e2e pod runs on the cluster, since runs share the `tm-e2e` principal and each removes what an earlier one left. A pod that cannot start (a missing image, a failed init container) fails the runner within 300 s (`START_TIMEOUT_SECONDS`) with the pod's events, and `activeDeadlineSeconds` bounds a run (1200 s critical, 7200 s full).

**The e2e has its own Polaris principal.** The pod's init container alone holds the platform's credential (`table-maintenance-polaris-credential`): it runs `python -m e2e.setup_principal`, which keeps or creates principal `tm-e2e` with principal role and catalog role `tm_e2e` (`CATALOG_MANAGE_CONTENT` on `iceberg`) and the `service_admin` principal role (to read back the catalogs the round trip creates), resets its credentials (Polaris lets only a principal rotate its own) and writes them to an in-memory volume the scenarios read. The principal stays between runs; its credentials change on each. Storage is read with the RustFS key in `table-maintenance-s3`, the platform's only account.

**The e2e may restart the worker, watch the maintenance jobs and hold their queue, and nothing else in the cluster.** `run.sh` applies `e2e/rbac.yaml` before the pod: the ServiceAccount `table-maintenance-e2e`, a Role in `lakehouse-control-plane` that allows only `get` and `patch` on the Deployment `table-maintenance-worker`, which `test_worker_restart_schedules.py` restarts as `kubectl rollout restart` does (it changes the pod template's `restartedAt` annotation), and a Role in `lakehouse-maintenance-operations` that allows `get`, `list` and `watch` on SparkApplications, `get` and `list` on pods, and `get`, `list`, `create` and `delete` on Volcano PodGroups. The pod mounts that account's token; it reads no Secret, execs into no pod, and changes no SparkApplication, pod or other Deployment. `SparkJobWatch` watches the SparkApplications in a thread to count a table's jobs at once (a job carries no table label, so it is tied to its run by `table-maintenance/run-id`). A **queue holder** (`QueueHolder`, `tm-e2e-holder-<suffix>-<scenario>`) is a PodGroup with no pods that asks the whole normal queue (cpu 2, memory 2304Mi), so Volcano admits it and keeps every later job of that queue `Pending` until the scenario deletes it; a holder a cut-short run left is deleted by `run.sh`'s exit, once the run knows it is the only one (a pod killed outright runs no cleanup of its own), and otherwise by the next session's sweep, by its name and labels.

| Marker | Scenario | What it checks |
|---|---|---|
| `critical` | `test_platform_answers.py` | the API lists the catalog and its namespaces, the e2e principal reads `iceberg` with PyIceberg, Temporal describes the platform's namespace |
| `critical` | `test_catalog_round_trip.py` | a catalog `tm_e2e_catalog_<suffix>_round_trip` at `s3://tm-e2e-catalogs/<catalog>`, two namespaces, a `day(order_ts)` table at a custom location, a generic table and a view, each written through the API and read back from Polaris; the stale-update 409s; the non-empty namespace delete passes Polaris's status and message; each delete is followed by Polaris's 404 |
| `critical` | `test_discovery_policies.py` | a policy with no rule is 422, at create and at save, and stores nothing; an exclude-only policy is stored; under `include *`, `exclude *_tmp`, `include orders_tmp` the last matching rule decides (`a_tmp` left out, `orders_tmp` and `orders` managed); a policy attaches to an empty namespace, which lists its catalog for scanning, with no id of its own, while a missing place is 404 and a namespace level holding a `.` is 422, storing nothing and starting no scan; a save makes version 2 and version 1 stays readable, a stale save is 409; deleting a policy still attached is 409 naming each place, and once detached from all it deletes |
| `critical` | `test_maintenance_policies.py` | the default maintenance policy has the target-state shape (its seeded values while at version 1); the platform settings list the four cooldowns, and the partition selection group, between the cooldowns and discovery, holds the values the pods were given; a policy with `retain_last` or an unknown option is 422 and not stored |
| `critical` | `test_removed_routes.py` | `/mappings`, both `applicable-policy` routes, `discovery-rules`, `compaction-rounds` (also one round), `scheduler-settings`, a table's `health`, `storage` and `compaction-candidates`, and the old per-operation result route answer the router's own 404 |
| `critical` | `test_maintenance_requests_refused.py` | priority `P4` for a table and `P9` for a manual run are 422; an unknown `rc-` id is the handler's 404 |
| `critical` | `test_effective_policies.py` | by location: a table's own maintenance policy wins over its namespace's while its sibling and the discovery kind keep theirs, each entry naming its `target` and no `attachment_id`; detaching falls back (a place holding another policy is 404, a bad target type 422, attaching again is still one place); nothing attached gives the maintenance default and no discovery policy, also for a nested namespace; a missing place is 404; a dropped table holds no policy any more, and a dropped namespace stays listed `orphaned`, keeps the policy from being deleted and still detaches |
| `full` | `test_discovery_lifecycle.py` | attaching an including policy to a namespace manages its tables with `decided_by` (policy, version, rule position) and lists the catalog in `scanned-catalogs`, leaving another namespace's table unmanaged with no `decided_by`; an exclude-only policy attached to one table unmanages only it and stops its workflow; a save that excludes a managed table unmanages it by rule 2, one that matches nothing unmanages the rest, and restoring the rule manages them again; detaching both unmanages all and drops the catalog from `scanned-catalogs`; a namespace's exclude-only policy leaves its table out under a catalog-level include; a discovery policy attached to a table the platform never heard of registers it (`undecided`, or already `managed`), manages it by rule 1, and detaching it unmanages it |
| `full` | `test_discovery_unreadable_catalog.py` | with `catalog_admin`'s content grants revoked, attaching and the effective policies are 403 with the reason and nothing is stored; a policy save rescans and records `cannot_access` (keeping the last completed scan's time), cleared by the next scan once the grants are back; a round of the schedule records `cannot_access` for an unreadable catalog and still completes a readable one's scan, each scan's parent being that round |
| `full` | `test_policy_records.py` | a dry-run table's reconciliations: `table_managed` when it becomes managed and nothing for a later discovery scan; each attach and save of a nearer policy (`policy_changed` with its `mp-` id, version and target); version 1 stays readable after a save, version 99 is 404; dropping `rewrite_data_files` records it `off` with no run |
| `full` | `test_table_information.py` | a dry-run table managed while empty (every metric 0), then written, evolved (rename, `int` to optional `long`, a nested column) and moved from `day` to `hour` partitions: the metrics after a reconcile match the snapshot's totals and the exporter prints its 17 samples (an unmanaged table answers nulls, an unknown uuid 404); the record's `decided_by` (policy, version 1, rule 1) and `P3`; the catalog's uuid, snapshots and properties match PyIceberg's; schema and partition spec versions compared by id; each commit's schema id |
| `full` | `test_metric_trends.py` | a dry-run table written after it is managed and reconciled shows the new count in `metrics/current` and, once Prometheus scraped it, as the newest point of the hour's trend |
| `full` | `test_worker_restart_schedules.py` | the one discovery schedule `table-discovery`, deleted in Temporal, is rebuilt as configured and not paused once the restarted worker Deployment is available; triggering it starts a round that completes and starts, as its child, a scan of a catalog holding a discovery policy, which completes |
| `full` | `test_scheduled_partition_compaction.py` | a `region`-partitioned table with four appends (`north`, `o'neil`) under a policy of one reducible file per partition, checked every 300 s and 90 s after its first unchecked commit (the window outlasts the quiet period, so the check does not wait for the schedule): the `table-discovery` schedule exists, a scheduled compaction succeeds with timed attempts and compacts spec 0's partitions including `o'neil`, the effective policies are the table's and its namespace's, the file count falls, current metrics carry `data_files` |
| `full` | `test_manual_maintenance.py` | an orders table with 20 single-row appends and a delete under a `dry_run` policy; 65 s after the last write a manual request runs all four operations: one run per operation of one plan, in plan order, timed, a whole-table compaction (`partitions == []`), linked in the reconciliation; reconcile now is recorded; files, snapshots and the objects under `data/` shrink as the runs' metrics account for; the catalog API's metadata agrees with PyIceberg's counts; commits come newest first; Temporal finds both workflows by `TableUuid`; every id the API returned is prefixed (ADR 0011). While it runs, a watch on the SparkApplications sees one job of the table at a time, in plan order, each named `tm-<op>-<run suffix>-a<attempt>` as its attempt records; the first job's PodGroup is in queue `table-maintenance` with class `table-maintenance-p3` and the size's resources, its pods use the `volcano` scheduler and carry no class, and its driver reads `FallbackToLogsOnError` and 1152Mi; a raise to `P1` reaches the later runs; one `TableMaintenanceWorkflow` runs, whose search attribute and summary list the plan; a reconcile asked for during the plan is recorded after its last run; every run reports procedure metrics; every reconciliation reads the same by id |
| `full` | `test_partition_cap_and_order.py` | e2e profile. 13 appends leave `rNN` with `NN + 1` files: right after them a reconcile reads `waiting_for_writes` until `r02`'s quiet period ends, starting nothing; once quiet, one reconcile starts a compaction of the ten partitions with most files (`r03`..`r12`, the cap leaving `r02` out without counting it as waiting) and an expiry after it, each with its own run; metrics fall; the next check inside the cooldown is `cooling_down`, and the one after compacts `r02` alone. The policy turns partial progress off (see `docs/agents/known-follow-ups.md`) |
| `full` | `test_partition_quiet_and_max_wait.py` | e2e profile. `cold` and `hot` both wait for their writes; once `cold` is quiet it is compacted alone while `hot`, written every 15 s by a background writer, waits; `hot` is compacted once over the target for the longest wait, at attempt 1, every append committed |
| `full` | `test_partition_spec_evolution.py` | e2e profile. A `day(ts), bucket(id, 4)` table whose spec drops the bucket: one compaction records spec 0 with both fields and four partitions and spec 1 with the day alone, and spec 0 ends with fewer files |
| `full` | `test_maintenance_queue.py` | with a queue holder in place, a P3 job waits `Pending`; a P0 request moves it to `table-maintenance-urgent` with class `table-maintenance-p0` under the same attempt and name, and it runs while the hold stays; then a P3 run and a run of a table set to P1 wait `queued` (the P1 job carries `table-maintenance-p1`); after the release the P1 run goes first and the P3 one only after it ended |
| `full` | `test_maintenance_cancel.py` | a manual plan of three runs, cancelled through Temporal once the first job was submitted: the first run ends `cancelled` with a finish time, its last attempt failed as `cancelled` with next step `cancelled`, the others `skipped` with the reason, none `pending`, no job of them left, the reconciliation still running |
| `full` | `test_reconciliation_triggers.py` | a dry-run table checked every 60 s gets a `schedule` record; with the schedule at an hour, ten appends give one `catalog_commit` record counting 10, 30 s after the first, whose compaction is `would_start` with no run; with the commit window removed, three appends wait for the schedule |

`full` runs every scenario (`-m "critical or full"`). **Each scenario uses names of its own run and undoes what it made, passed or failed.** A module that attaches discovery or maintenance policies, scans or compares against the defaults works in a catalog of its own, `tm_e2e_catalog_<suffix>_<module>` at `s3://tm-e2e-catalogs/<catalog>` (`OwnedCatalog`, dropped after the module's last scenario), so it never changes how `iceberg` is scanned. A scenario that makes its catalog unreadable takes only `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_METADATA` from its `catalog_admin` role, never the role or `CATALOG_MANAGE_ACCESS`, and grants them back as its first undo; dropping an e2e catalog grants them back first too, since Polaris lets nobody empty a catalog without them. A full scenario's namespace is `e2e_<suffix>_<scenario>` with a discovery policy `tm-e2e-<suffix>-<scenario>` attached to it; its cleanup detaches and deletes the discovery policy, waits until the table is unmanaged and its reconciliation stopped (so the platform default never plans a job on a half-removed table), detaches and deletes the maintenance policy, drops the table and removes its storage, then removes the namespace's storage and drops the namespace. A cleanup step that fails fails the scenario, naming the step. **A run that is cut short still cleans up**: a SIGTERM (the pod's deadline, an eviction, a delete) interrupts pytest, which tears down the running scenario's cleanup within the pod's 900 s grace period; and before any scenario starts, every run removes what an earlier run left under the e2e's own names (`OwnedNames`: namespaces `e2e_<suffix>_<scenario>`, policies `tm-e2e-<scenario>-<suffix>` and `tm-e2e-<suffix>-<scenario>`, catalogs `tm_e2e_catalog_<suffix>_<scenario>`, queue holders `tm-e2e-holder-<suffix>-<scenario>` (first), the tables in them waited on until unmanaged, and their storage), in the same order, and prints each removal. A scenario's namespace storage is the namespace's own `location`, refused when it is not the namespace's directory, so a cleanup never removes a wider prefix. The platform's own records of the dropped tables (the `dropped` table, its runs and reconciliations) stay: the platform keeps that history. If a Spark driver cannot deliver its result callback, the polling fallback records the run `succeeded` with `{"completed_without_callback": 1}`; the checks of the numbers that callback would have sent are then skipped.

## Spark event logs

Every maintenance SparkApplication writes its Spark event log to the RustFS bucket `spark-event-logs` (wave `20-rustfs`, 3-day expiry): `spark.eventLog.enabled=true`, `spark.eventLog.dir=s3a://spark-event-logs/` (`spark.event_log_dir`), `compress=true` with `zstd`, `logStageExecutorMetrics=true` and rolling at `128m`. S3A gets `fs.s3a.endpoint` / `fs.s3a.endpoint.region` from the catalog settings, `path.style.access`, `connection.ssl.enabled=false` for an `http://` endpoint and `EnvironmentVariableCredentialsProvider`, which reads `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the `table-maintenance-s3` Secret the driver and executor already load. The jars are `hadoop-aws` 3.4.1 (the Hadoop bundled in `apache/spark:4.0.0`, `spark.hadoop_version`) and `s3-transfer-manager` 2.33.0 (`spark.aws_sdk_version`): `iceberg-aws-bundle` 1.10.1 already ships AWS SDK v2.33.0 but not the transfer manager, which S3A uses for uploads and the rename copy.

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
