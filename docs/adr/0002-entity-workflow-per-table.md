# 2. One long-lived reconciliation workflow per table

Date: 2026-10-24

Status: Accepted

## Context

The previous table maintenance backend worked like Airflow: an operator created a `Job` with a cron, a scheduler polled the database, and an outbox chained the steps that submitted a Spark job. Each table has its own cadence, cooldowns and failure backoff, and two maintenance operations must never run on the same table at once. A run must never be lost when Spark crashes or a worker restarts.

Temporal is deployed in the cluster (`temporal` namespace).

## Considered options

1. A central scheduler that periodically scans all tables and submits due work, with database locks to prevent overlapping runs.
2. A cron schedule per table that starts a short workflow on each tick.
3. One long-lived entity workflow per table that waits on a timer or signals, plans, and starts one child workflow per maintenance run.

## Decision

Option 3. Each `ACTIVE` or `PAUSED` table has exactly one `TableReconciliationWorkflow` with ID `table-reconciliation:table-uuid={uuid}`. It wakes on its reconcile timer (default 1 hour) or on the signals `settings_changed`, `table_updated`, `trigger_now`, `pause`, `resume` and `maintenance_finished`. On wake it runs the planning activity, which reloads the table from the database and observes it in the catalog. A non-empty plan starts a `TableMaintenanceWorkflow` child (`table-maintenance:table={catalog}.{namespace}.{table}:run={run_id}`, `ParentClosePolicy.ABANDON`). The ID carries the table name as of the run start, so it cannot be rebuilt from the run ID: the reconciliation workflow keeps the ID of its in-flight child and cancels by it, and the table maintenance run stores it (`execution_ref`, then called `workflow_id`), which the Spark result callback uses to signal the run. The child signals `maintenance_finished` back to the parent by workflow ID. While a run is in flight nothing else is planned, and a manual trigger is kept until the run finishes. The workflow uses continue-as-new to bound its history, and ends when the table is dropped or excluded.

Spark capacity is shared through one `TableMaintenanceAdmissionWorkflow` (`table-maintenance-admission`, a global semaphore, default limit 2, lease 22500 s).

Workflow and schedule IDs are a name followed by `key=value` segments joined by `:`. Table discovery runs from one schedule per catalog (`table-discovery:catalog={catalog}`, which Temporal suffixes with the firing time); an ad-hoc discovery adds `:trigger=adhoc` (and `:namespace={namespace}` when scoped) so it never collides with the scheduled runs. Every workflow starts with a static summary for the Temporal UI: the table name (reconciliation), the table and its operations (maintenance), the catalog or namespace (discovery) and the limit (admission).

## Consequences

- One run per table at a time is a property of the workflow, not of a database lock.
- Durable timers and retries replace the polling scheduler and the outbox. A worker restart resumes every table where it was.
- The database stays the authority on status and settings. Signals only wake the loop, so a lost or duplicate signal costs at most one extra plan.
- Workflow code must stay deterministic, and changing it needs care with running histories (versioning or patching once tables are long-lived in production).
- There is one running workflow per table. That is cheap in Temporal but has to be counted for capacity at large table counts.
- A child that never reports back is given up once its worst case has passed (per planned operation: three attempt deadlines, the two backoffs and a 1 hour margin, about 19 hours), so a terminated child cannot wedge its table forever. The parent first cancels the child, whose cleanup records the result, frees its admission slot and deletes its Spark job, and waits up to 15 minutes for its report, so the next run does not overlap the old Spark job.
