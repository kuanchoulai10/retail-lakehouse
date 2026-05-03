# Retail Lakehouse — Iceberg Table Maintenance

An internal platform tool for managing scheduled maintenance (compaction, snapshot expiry, etc.) on Apache Iceberg tables. Single shared workspace — no tenant isolation. Users authenticate via company SSO; the tool records `actor` on every mutation for audit.

## Language

**Catalog**:
A configured connection to an external Iceberg catalog (initially only Apache Polaris) — owns the connection settings, credentials reference, and implementation kind. Aggregate root. No status enum: a Catalog is permanent once configured and can only be hard-deleted after all its **Tables** are removed. Credentials rotation updates `credentials_ref` in place; transient connection failures are an infra concern, not a domain state.
_Avoid_: CatalogRegistration, CatalogConnection, CatalogConfig

**CatalogImplKind**:
Enum of supported catalog backends; currently only `POLARIS`. New backends add a value plus a new concrete `ConnectionConfig` subtype; no abstract base until the second backend exists (YAGNI).

**Namespace**:
A path of one or more identifiers locating a group inside a **Catalog** (e.g. `("analytics",)` or `("region", "country", "team")`). Value object. Mirrors Iceberg/Polaris nested namespaces; deliberately not called "database".
_Avoid_: Database, Schema (when meaning a namespace path)

**TableIdentifier**:
The fully-qualified pointer to a table: (catalog_id, **Namespace**, name). The aggregate id of **Table**.

**Table**:
An Iceberg table the operator has enrolled — the gatekeeper for any change targeting that table. Aggregate root; carries Iceberg-side state (properties, schema, current snapshot id) plus tool-side metadata (enrolled_at, enrolled_by). No status enum: a Table is permanent once enrolled and can only be hard-deleted after all its **Jobs** and **Monitors** are removed. Every mutation goes through this aggregate; batched property changes accumulate in-memory and are flushed atomically by the repository (single underlying `ALTER TABLE` call).
_Avoid_: ManagedTable, TableSubscription, EnrolledTable

**Snapshot** (Iceberg term):
A point-in-time view of an Iceberg table's data files, produced by every commit. Visible on **Table** (current snapshot id) and queryable on demand via the catalog adapter. Not an aggregate.

**Job**:
A maintenance task definition attached to one **Table** — owns job type (compaction, expire snapshots, etc.), runtime config, lifecycle (active/paused/archived), and an optional self-cron (`CronExpression | None`). Independent aggregate root; soft-references its **Table** by **TableIdentifier**. May only be created against an existing **Table** (enforced by the create-job use case). Can be triggered by manual call, its own cron, or a **Monitor**.

**JobRun**:
A single execution of a **Job** — owns the run's status (PENDING → RUNNING → COMPLETED/FAILED/CANCELLED), trigger source, and result. Independent aggregate root. **Runtime-agnostic**: the aggregate does not know or care which runtime executed it.

**Monitor**:
An observation rule attached to one **Table** — owns a condition expression, an evaluation schedule (cron), optional alert config, up to 5 target **Job** ids it triggers when the condition holds, and a `last_observed_snapshot_id` for change detection between evaluations. Independent aggregate root; soft-references its **Table** by **TableIdentifier**. May exist purely to alert (no target jobs).

**TriggerSource**:
The cause of a **JobRun** — `MANUAL`, `CRON`, or `MONITOR`. Recorded on `JobRun.trigger_type` plus an optional `trigger_ref` (cron expr or originating monitor id). Two schedulers (one for cron-driven Jobs, one for cron-driven Monitors) are the producers; the JobRun is the receipt. Not an entity or aggregate.

**RuntimeKind**:
A **Job**-level enum naming an execution backend (currently only `SPARK_ON_K8S`). Application services dispatch to the matching outbound adapter based on this value. Domain expresses no rules about which job types can use which runtimes.

**RuntimeConfig**:
Abstract base value object describing runtime-specific settings on a **Job**. Concrete subtype today: **SparkOnK8sRuntimeConfig** (image, driver/executor cpu & memory, etc.). Adding a runtime = new `RuntimeKind` value + new `RuntimeConfig` subtype + new outbound adapter; aggregates do not change.

**Actor / ActorId**:
The user who initiated a domain action (configured the Catalog, created the Job, manually triggered the run). Value object recorded on domain events for audit. The User itself is owned by company SSO/IDP — not a domain aggregate here; we only carry the id.
_Avoid_: User (modelled here), Owner, CreatedBy as a separate concept

## Relationships

- A **Catalog** contains a recursive tree of **Namespaces** with **Tables** at the leaves
- A **Table** belongs to exactly one **Catalog** (via `TableIdentifier.catalog_id`); a **Catalog** with any **Tables** cannot be hard-deleted (must be disabled instead)
- A **Table** has many **Jobs** and many **Monitors**; both are independent aggregates linked by **TableIdentifier**, not children of the Table
- Creating a **Job** or **Monitor** requires the target **Table** to already exist (enforced by the create use case)
- A **Monitor** holds up to 5 target **Job** ids; the link is unidirectional (Monitor → Jobs) — Jobs do not back-reference monitors
- A **JobRun** records its **TriggerSource** (`MANUAL`/`CRON`/`MONITOR`) and an optional `trigger_ref`
- Every mutating domain action carries an **ActorId** for audit; mutations to a **Table**'s Iceberg-side state go through the Table aggregate, which the repository flushes atomically

## Patterns

**Two lifecycle classes — pick by whether the aggregate produces immutable history.**

- **Reference targets only** (no history): `Catalog`, `Table`. No status enum. Permanent once created; only hard-deletable after every referring aggregate is removed (delete use case enforces with a `count_by_*` query against the referrer repo). No soft-archive.
- **Producers of immutable history**: `Job`, `Monitor`. Have `ACTIVE / PAUSED / ARCHIVED` status. `ARCHIVED` is terminal. No hard delete — the aggregate stays so its `JobRun` / `MonitorEvaluation` records keep a valid pointer. UI hides archived by default.
- **Immutable history records themselves**: `JobRun` (and future `MonitorEvaluation`). Append-only; never deleted.

**Trigger-time gate.** When a scheduler or upstream event tries to advance a `Job` or `Monitor`, the use case loads the target aggregates and verifies they are usable (`Job.status == ACTIVE`, `Table` exists, etc.). Failures emit a `*TriggerSkipped` event with a `reason` rather than mutating any aggregate. Reasons so far: `job_paused`, `job_archived`, `table_missing`, `max_active_runs_reached`.

## Workflows

**Triggering a Job → JobRun (event-driven, one aggregate per transaction):**

1. `TriggerJobUseCase` loads the **Job**, calls `job.trigger(...)` (validates ACTIVE + active-runs ceiling), saves the Job → outbox emits `JobTriggered`.
2. `CreateJobRunUseCase` (handler on `JobTriggered`) creates a **JobRun** in `PENDING`, saves it → outbox emits `JobRunCreated`.
3. `SubmitJobRunUseCase` (handler on `JobRunCreated`) hands the run to the runtime adapter matching `Job.runtime_kind`.
4. Runtime callbacks/poll drive the **JobRun** state machine (`mark_running` / `mark_completed` / `mark_failed`).

Each use case touches one aggregate; handlers must be idempotent (outbox may redeliver).

## Flagged ambiguities

- "Catalog" was used to mean both the configured connection AND the external system. Resolved (in single-workspace context): the **Catalog** aggregate is "our configured connection"; the external system is reached through the catalog adapter and has no separate domain noun.
- "Database" was proposed as the layer between catalog and table. Resolved: there is no `Database` — Iceberg uses recursive **Namespaces**. UI may say "database"; the domain does not.
- "Table" briefly split into Table (read-model) + ManagedTable (aggregate). Resolved: collapsed back to a single **Table** aggregate.
- "Tenant" was modelled as first-class for a SaaS framing. Resolved: dropped — this is an internal single-workspace tool, no tenant concept; **ActorId** covers audit.
