# Table Maintenance Control Plane — Design

**Date**: 2026-10-24
**Status**: Draft
**Supersedes (for table maintenance)**: the Airflow-style `Job` / `JobRun` / scheduler / outbox design in `src/table-maintenance` (its ADRs 0001–0003 were deleted as obsolete)

## Intent

Iceberg tables in this lakehouse degrade on their own: streaming writes (Debezium → Iceberg sink) produce many small files and delete files, manifests multiply, and snapshots and orphan files pile up. The goal is a control plane that **finds tables automatically, decides per table what maintenance is due, runs it on Spark, and records what happened**, with the operator steering it through an API (a UI comes later and is the long-term primary interface).

The previous implementation modelled this like Airflow: a user creates a `Job` with a cron, a scheduler polls, an outbox chains `JobTriggered → JobRunCreated → SubmitJobRun`. The new model is **continuous reconciliation**: every managed table has its own long-lived Temporal workflow that periodically (or on event) compares the table's observed state against its maintenance policy and acts. The old code may be rewritten freely; it must stay Clean Architecture (see `CLAUDE.md`).

## Goals (milestone 1)

End-to-end on minikube:

1. Through the API, a discovery rule is created that includes only a dedicated test table (pattern), with a template. Then the test table is created through Trino and written to (deliberately producing small files, partitioned with at least one transform).
2. The Polaris event reaches the control plane, the table is discovered, matched against the rule, and registered in the Table Registry.
3. The table's maintenance settings are generated automatically from a policy template and are visible in the DB / API.
4. Temporal runs the table's reconcile workflow (visible in the Temporal Web UI).
5. All four operations run: `rewrite_data_files` (partition-level), `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`.
6. The effect is real: object listings in RustFS change (small files merged, expired snapshots / orphan files gone) and Iceberg metadata reflects it.
7. Through the backend API the operator can change discovery rules, templates, a table's settings, pause/resume a table, and trigger maintenance manually; changes persist in the DB and change subsequent behaviour.

## Non-goals (milestone 1)

- UI.
- Notifications / alerting on failure.
- Multi-tenancy (single tenant; keep identifiers and schema so a tenant dimension can be added later).
- Auto-removing tables that stop matching discovery rules (see "Lifecycle").
- Template → table propagation (templates are copied once; see "Maintenance policy").
- Kafka as a maintenance-request queue.

## Anti-goals

- Two maintenance operations running concurrently on the same table.
- A maintenance run silently lost (Spark crashed, worker restarted) with the table never retried or the run left "running" forever.
- Hard-deleting registry rows: history must stay attached to its table.
- Domain/application code importing Temporal, FastAPI, PyIceberg, Kafka, or Kubernetes clients.

## Constraints

- Clean Architecture with the strict no-skip-layer rule, `import-linter`, DDD base types in `base/`, naming conventions (`{Aggregate}Repo`, `{Verb}{Noun}Gateway`, DTO suffixes), one object per file, TDD — all as in `CLAUDE.md`.
- Python (backend is `requires-python >=3.14`), FastAPI, SQLAlchemy, PyIceberg, Temporal Python SDK (`temporalio`). The builder must confirm the `temporalio` wheel supports the chosen Python version; lowering the Python floor is acceptable if needed.
- Temporal server is already deployed: `temporal-frontend.temporal.svc.cluster.local:7233`, Temporal namespace `default` (waves `20-temporal-db`, `21-temporal`).
- Spark: Spark Operator (wave 11), image based on `apache/spark:4.0.0` with the Iceberg 1.10 runtime (`src/table-maintenance/runtime/spark`, which already renders the four `CALL ... system.*` procedures).
- Catalog: Polaris 1.8.0 REST (`lakehouse-catalog` ns), warehouse `iceberg`; storage RustFS S3 (`rustfs.object-storage.svc:9000`).
- Kubernetes namespaces: control plane in `lakehouse-control-plane`, Spark jobs in `lakehouse-maintenance-operations`, Temporal in `temporal`.
- Deployment as a **Helm chart**, installed by the `platform/25-lakehouse-control-plane` wave's `bootstrap.sh` (deploy-by-scripts path, `KUBE_CONTEXT` required, `validate.sh`, wired into `tasks/apps.yml`). The chart includes the control-plane Postgres.
- The on-hold `platform/25-table-maintenance` and `platform/25-tbl-maint-*` dirs are replaced by this wave and removed at the end.

## Architecture

```
Polaris ──(Kafka event listener)──> topic polaris-catalog-events
                                         │
                              [event-consumer]  (lakehouse-control-plane)
                                         │ start / signal (Signal-With-Start)
                                         ▼
 Temporal Schedule ──> DiscoveryWorkflow ──> Table Registry (Postgres)
                              │  start / stop per table
                              ▼
                 TableReconcileWorkflow  (one per table, id = table UUID)
                    timer + signals, decides what is due
                              │ child (ABANDON), signals result back
                              ▼
                 MaintenanceWorkflow  (one per maintenance run)
                    acquire global capacity → submit SparkApplication
                    → wait for callback / poll status → record result
                              │
                              ▼
            SparkApplication in lakehouse-maintenance-operations
            runtime/spark: CALL polaris.system.<procedure>(...)
                              │ POST result
                              ▼
                         [api]  ──signal──> MaintenanceWorkflow

 [api] (FastAPI): rules, templates, tables, settings, manual trigger, run history
```

### Components (one image, selected by an env var, like today's `GLAC_COMPONENT`)

| Component | Role |
|---|---|
| `api` | FastAPI. CRUD for discovery rules, policy templates, registered tables and their settings; pause/resume; manual trigger; run history; Spark result callback endpoint. Signals/starts workflows through a gateway port. |
| `worker` | Temporal worker hosting all workflows and activities. |
| `event-consumer` | Consumes `polaris-catalog-events`, maps table-level events to Temporal calls. |
| Postgres | Control-plane DB (registry, rules, templates, settings, runs). Part of the chart. |

### Clean Architecture mapping

- **Domain**: aggregates and policies below; pure evaluation logic (discovery rule matching, "is maintenance due", reducible-file computation, partition predicate building) lives here or in application services and is unit-tested heavily.
- **Application**: use cases (register table, mark dropped, update settings, evaluate table, plan maintenance, record run result, …) and ports. Ports include catalog reads (`ReadCatalogGateway`-style), Spark submission (`SubmitMaintenanceJobGateway`-style), workflow control (start/signal workflows) and repositories.
- **Adapters**:
  - inbound: FastAPI routes, Kafka consumer loop, **Temporal workflows and activities**. Workflows are inbound adapters: they orchestrate by calling activities; activities call use cases. Workflow code must stay deterministic and contain no business rules beyond sequencing.
  - outbound: SQLAlchemy repos, PyIceberg catalog gateway, Kubernetes SparkApplication gateway, Temporal client gateway (used by `api` and `event-consumer`).
- **Bootstrap**: composition roots per component.

Exact port/use-case names are left to the builder, following the naming conventions.

## Domain model

### Discovery rules

- Fields: `priority` (int, lower = evaluated first), `effect` (`INCLUDE` / `EXCLUDE`), `catalog` pattern, `namespace` pattern, `table` pattern (glob), `template` (required when `effect = INCLUDE`), `enabled`.
- Matching: rules are evaluated in priority order; the **first matching rule decides**. No match → not maintained.
- **No rules are installed by default.** A fresh onboard maintains nothing until the operator creates rules through the API. In particular the CDC table `inventory.orders` (continuously written by the Iceberg sink) is not maintained in milestone 1; the end-to-end check uses a dedicated test table plus a rule created through the API that includes only that table.
- A global **discovery switch** (on/off). Off = the discovery Schedule is paused and the event consumer ignores "new table" hints. Existing registered tables keep being reconciled.

### Policy templates

- Named, reusable maintenance settings (all four operations, see below).
- When a table is registered via an `INCLUDE` rule, the template is **copied** into the table's own settings. After that the two are independent: editing a template never changes existing tables.

### Managed table (Table Registry)

- Identity: the Iceberg **`table-uuid`** from table metadata. Name (`catalog`, `namespace`, `table`) is a mutable attribute.
- `status`: `ACTIVE`, `PAUSED` (by operator, temporary), `EXCLUDED` (operator decided this table is not maintained), `DROPPED` (table no longer exists). Rows are never deleted.
- `selection`: `AUTO` (decided by discovery rules) or `MANUAL` (operator pinned it). Discovery never changes a `MANUAL` table.
  - Manual include: the operator registers a table that no rule includes (`MANUAL` + `ACTIVE`, settings copied from a chosen template).
  - Manual exclude: the operator excludes a table, registered or not (`MANUAL` + `EXCLUDED`; an unregistered table gets a row without settings). Its reconcile workflow is stopped (like `DROPPED`); discovery skips it.
  - Reset: the operator can return a `MANUAL` table to `AUTO`; discovery rules are then re-applied to it immediately.
  - The reconcile workflow runs only for `ACTIVE` and `PAUSED` tables.
- Holds the table's own maintenance settings (copied from a template, then editable).
- The old ADRs (0001–0003) were deleted as obsolete. The builder should record the key decisions of this design (table identity by UUID, status lifecycle, entity reconcile workflow) as new ADRs in `docs/adr/`.

### Maintenance settings (per table)

Every operation has `enabled`, and a **minimum interval** (cooldown) between runs of that operation.

| Operation | Settings | "Due" when |
|---|---|---|
| `rewrite_data_files` | `scope` = `PARTITION` or `TABLE`; `target_file_size_bytes` (default: table property `write.target-file-size-bytes`, else 512 MiB); thresholds: minimum reducible files per partition (and/or table) | any partition (or the table) meets the threshold |
| `rewrite_manifests` | thresholds on manifest count / small-manifest count (exact metric left to the builder, from the `manifests` metadata table) | threshold met |
| `expire_snapshots` | `older_than` (duration), `retain_last` (int) | there are snapshots that would be expired |
| `remove_orphan_files` | `older_than` (duration, **enforced minimum 1 day**), interval default 7 days | interval elapsed |

Reconcile interval per table (default 1 hour).

**Reducible files** (per partition; table scope = same computation over the whole table):

```
total_files    = data_files + delete_files
expected_files = ceil(total_data_bytes / target_file_size_bytes)
reducible      = total_files - expected_files
```

Inputs come from Iceberg metadata via PyIceberg (`inspect.partitions()` / manifests): data file count, position + equality delete file counts, total data bytes, per partition and spec.

### Maintenance run (history)

- One run record per plan: table UUID, trigger (`SCHEDULED`, `EVENT`, `MANUAL`), overall status, timestamps.
- Each run has **one record per operation**: operation, status (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `SKIPPED`), attempts, timestamps, Spark application name(s), result metrics returned by the procedure (e.g. `rewritten_data_files_count`, `added_data_files_count`, deleted file counts), error message.
- Run overall status: `SUCCEEDED` if all operations succeeded, `PARTIALLY_FAILED` if some failed, `FAILED` if all failed.
- Append-only.

## Behaviour

### Event consumer

Polaris 1.8.0 events observed on `polaris-catalog-events` (sampled 2026-10-24): JSON with `event_type`, `catalog_name`, `namespace` (array), `table_name` (present on table-level events), `timestamp`, `event_id`. **`BEFORE_CREATE_TABLE` carries no `table_name`, and no `AFTER_CREATE_TABLE` was observed** for a Trino-created table (it shows up as `AFTER_UPDATE_TABLE` commits). Therefore events are treated as **hints, the catalog is the source of truth**:

- Table-level events (`AFTER_UPDATE_TABLE`, `AFTER_DROP_TABLE`, rename, …) for `(catalog, namespace, table)` → Signal-With-Start a short "check this table" path: load the table from the catalog; unknown UUID → evaluate discovery rules → register (if discovery is on); known UUID under a new name → update name (rename); not found → mark `DROPPED` after confirming by UUID scan.
- Namespace-level create-table hints without a table name → trigger a discovery scan of that namespace.
- Read/load events (`*_LOAD_TABLE`, `*_REFRESH_TABLE`, list/get) are ignored.
- `AFTER_UPDATE_TABLE` for an already-registered table may signal its reconcile workflow to re-evaluate early (subject to cooldowns), so write-heavy tables get attention soon after commits.
- Commits made by maintenance itself also produce update events; cooldowns and the "already running" check prevent loops.
- The full event type list, rename event shape, and consumer offset/commit strategy are left to the builder; verify against Polaris 1.8.0 source or live events.

### Discovery workflow

- Started by a Temporal Schedule (default every 10 minutes) and on demand (namespace hints, API).
- Lists tables in the catalog(s), evaluates rules for unregistered tables, registers `INCLUDE` matches with a template copy, starts their reconcile workflows.
- Safety net: registry `ACTIVE` / `PAUSED` tables whose UUID no longer exists in the catalog → `DROPPED`; renamed tables (same UUID, new name) → name updated.
- Does not remove tables that stop matching rules (milestone 1).

### Table reconcile workflow (entity workflow)

- Workflow ID derived from the table UUID; exactly one per registered table, started on registration, ended when the table becomes `DROPPED`.
- Loop: wait for the reconcile timer or a signal (`settings_changed`, `table_updated`, `trigger_now`, `pause`, `resume`, `maintenance_finished`).
- On wake: if `PAUSED` or a maintenance run is in flight → record and skip; else run the **evaluate** activity (reads observed state via PyIceberg, applies settings and cooldowns, returns a maintenance plan: which operations, and for compaction which partitions).
- If the plan is non-empty → start a `MaintenanceWorkflow` child with a deterministic ID (`ParentClosePolicy = ABANDON`), mark it in-flight, and wait for its `maintenance_finished` signal (the child signals the parent **by workflow ID**, so it works across Continue-As-New).
- Uses Continue-As-New periodically to bound history.
- A manual trigger from the API is a `trigger_now` signal naming the operations to run. **Manual means "always run"**: the named operations run regardless of cooldowns, due thresholds, or `enabled = false`; partition-scope compaction runs on the whole table. The only rule still enforced is one run per table at a time (a trigger while a run is in flight is queued or rejected; builder's choice, surfaced in the API response). Manual runs do update the operation's last-run time.

### Maintenance workflow

- Executes one plan. Operations in this order: `rewrite_data_files` → `rewrite_manifests` → `expire_snapshots` → `remove_orphan_files`.
- Before submitting Spark work, acquire a slot from a **global capacity limiter** (a singleton semaphore workflow; limit configurable, default 2 concurrent Spark jobs on minikube); release on completion, failure, or cancellation.
- Submit a `SparkApplication` in `lakehouse-maintenance-operations` with a deterministic name derived from the run ID (idempotent on activity retry).
- Completion: the Spark runtime POSTs its procedure result to the `api` callback endpoint, which signals the workflow; in parallel an activity polls the SparkApplication status so a crashed driver (no callback) is detected.
- **Retry**: a failed operation is retried automatically, **3 attempts in total** (first try + 2 retries), with backoff. After that the operation is `FAILED` and recorded. No notifications.
- **A failed operation does not abort the run**: the remaining operations still run in order (they are independent Iceberg procedures).
- **Failure backoff**: a failed operation's cooldown starts from its last attempt, like a success. In addition, each consecutive failed run of the same operation doubles that operation's cooldown (capped, e.g. 24 h); a success resets it. This keeps a permanently failing table from taking a global Spark slot every reconcile. The consecutive-failure count is stored per table and operation and exposed through the API.
- Records the run (status, metrics, error) through a use case.

### Partition-level compaction

Verified against Iceberg 1.10.0 source (Spark 4.0): `rewrite_data_files`'s `where` accepts the Iceberg system functions `years`, `months`, `days`, `hours`, `bucket(N, col)`, `truncate(W, col)` and converts them into partition filters (see `SparkV2Filters`, `TestRewriteDataFilesProcedure`). Rules the predicate builder must follow:

- Qualify functions with the catalog name: `polaris.system.bucket(16, id) = 3`.
- `days` returns DATE: `polaris.system.days(ts) = DATE '2026-10-24'`; `years` / `months` / `hours` / `bucket` compare to ints (since epoch / bucket number); `truncate` and identity compare to source-typed literals.
- Null partition values: use the source column, `col IS NULL` (`system.fn(col) IS NULL` is not converted).
- Pruning only applies when the predicate's transform exactly matches the spec's transform (`bucket[16]` ≠ `bucket[8]`, `days` ≠ `hours`).
- One partition = `AND` of its fields; several partitions = `OR`.
- Group selected partitions by spec ID; one procedure call per spec. For time transforms, also add a source-column range so files in other specs are pruned too.
- After the run, compare `rewritten_data_files_count` with the expected count and record both.

This builder is pure logic: implement it in the domain/application layer with extensive unit tests (every transform, nulls, multi-field, multi-spec).

## Deployment

- Helm chart for the control plane (location left to the builder, e.g. `platform/25-lakehouse-control-plane/chart/`), installed by `platform/25-lakehouse-control-plane/bootstrap.sh`; `validate.sh` checks every component and Postgres.
- Chart contents: Postgres (pinned image, PVC, Secret), `api`, `worker`, `event-consumer` Deployments, Service for `api`, RBAC allowing the worker to create/get/delete `SparkApplication`s in `lakehouse-maintenance-operations`, ServiceAccount for Spark driver/executors there, and config (Temporal address, Polaris URI/credentials, Kafka bootstrap, RustFS, capacity limit, defaults).
- All images pinned. The backend image is built locally and loaded into minikube (see the `minikube-deploy` skill / existing `build.sh`); the Spark runtime image likewise.
- An HTTPRoute for the API on `platform-gateway` is optional for milestone 1.
- Remove `platform/25-table-maintenance` and `platform/25-tbl-maint-*` once the new wave works; update `CLAUDE.md` Project Status and the wave README.

## Decided by the operator (KC)

- Namespaces: control plane in `lakehouse-control-plane`, Spark in `lakehouse-maintenance-operations`, Temporal in `temporal`.
- Event-driven discovery from Polaris events plus periodic discovery; per-table long-lived reconcile workflow triggered periodically or by events; Spark executes maintenance; results written back.
- Discovery rules with include and exclude, priorities, a way to switch discovery off, and manual per-table override.
- The four operations; compaction at partition level (or table level) using the reducible-files computation; expire snapshots by age and/or count; policy-based settings.
- Per-table settings generated automatically from a template; **copied once, independent afterwards**.
- Dropped tables: keep the row, mark it no longer maintained.
- Not matching policy anymore: defer.
- API now, UI later. Automatic retry, 3 attempts; no notifications.
- Old code can be rewritten heavily; must follow Clean Architecture. Deploy via Helm chart.
- No default discovery rules; milestone 1 is verified with a dedicated test table and an API-created rule for it.
- Manual trigger always runs the named operations (ignores cooldowns, thresholds, `enabled`); partition-scope compaction runs on the whole table.

## Calls made by the designer (reviewable)

- Table identity = Iceberg `table-uuid`; rename = name update on the same row.
- `status` enum (`ACTIVE` / `PAUSED` / `EXCLUDED` / `DROPPED`) instead of a `deleted` flag; `selection` `AUTO` / `MANUAL`; manual exclude also works for unregistered tables; `MANUAL` can be reset to `AUTO`.
- Run history: one record per run plus one per operation; a failed operation does not stop the others.
- Failure backoff: cooldown counts from the last attempt; consecutive failures double the cooldown (capped), success resets it.
- First matching rule by priority wins; default = not maintained.
- Discovery switch = pause Schedule + ignore new-table hints.
- Discovery runs every 10 minutes as a safety net; reconcile interval 1 hour; per-operation cooldowns.
- Events are hints; catalog is the source of truth.
- Kafka only as an event source, not as a maintenance queue.
- Child `MaintenanceWorkflow` with `ABANDON` + signal-back by workflow ID; one run per table at a time.
- Global capacity via a semaphore workflow, default 2.
- Spark result via API callback, plus SparkApplication status polling as a fallback.
- "3 attempts" = 3 in total.
- `remove_orphan_files` `older_than` ≥ 1 day, default weekly.
- Operation order: compaction → manifests → expire snapshots → orphan files.
- One image, three components (`api`, `worker`, `event-consumer`); Postgres inside the chart.
- Single tenant for milestone 1.
- Rewrite in place in `src/table-maintenance`, keeping `base/` and the architecture tests; drop `Job` / `JobRun` / scheduler / outbox.

## Left to the builder

- Port, use case, aggregate and table names (within the naming conventions); DB schema and migrations.
- Exact API resource paths and payloads (must be usable later by a UI).
- Thresholds/defaults for `rewrite_manifests`; default templates seeded on install.
- Kafka consumer group / offset handling, event-type mapping details.
- Temporal task queue names, timeouts, heartbeat intervals, Continue-As-New cadence.
- Chart layout, values structure, image build/tag scheme.
- Test data generation for the end-to-end check (Trino SQL that produces many small files across partitions, including a transformed partition spec).
- Order of implementation tasks (the plan).
