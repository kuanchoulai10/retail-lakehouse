# Two lifecycle classes: reference-clean delete vs archive-terminal

Aggregates fall into one of two lifecycle patterns, picked by whether they produce immutable history. **Reference targets only** (`Catalog`, `Table`) have no status enum and can only be hard-deleted after every referring aggregate is removed; the delete use case enforces the precondition with a `count_by_*` query. **Producers of immutable history** (`Job`, `Monitor`) carry `ACTIVE / PAUSED / ARCHIVED` status with `ARCHIVED` as a terminal state — they cannot be hard-deleted because their `JobRun` / `MonitorEvaluation` records must keep a valid pointer. **Immutable history records themselves** (`JobRun`) are append-only and never deleted.

## Considered Options

- **Unified reference-clean delete for everything.** Allow Job/Monitor delete when no JobRuns / MonitorEvaluations exist; otherwise force ARCHIVE. Rejected: introduces conditional lifecycle logic in delete use cases and two ways to "stop" a Job (delete vs archive), which UI and operators have to disambiguate.
- **Unified archive-terminal for everything.** Catalog/Table also get ARCHIVED status. Rejected: Catalog and Table have no history records pointing back to them, so an archive state is purely cosmetic — pure clutter without payoff.
- **Two lifecycle classes by aggregate role** (chosen). Two rules but each one is unconditional: delete-after-cleanup for pure references, archive-terminal for producers of history.

## Consequences

- ARCHIVED Jobs / Monitors stay in the database forever. UI must filter them out of the default list view.
- Triggering against an ARCHIVED Job emits `JobTriggerSkipped(reason=job_archived)` — the trigger-time gate covers archived Jobs without aggregate-level cascade.
- `Monitor.target_job_ids` never goes dangling: target Jobs always exist (just ARCHIVED). Cleanup of stale references is optional, not required.
- Deletion ordering becomes meaningful: to dispose of a Catalog, the operator first archives or deletes Jobs/Monitors per Table, then deletes Tables, then deletes the Catalog. The precondition-check use cases enforce this ordering with clear error messages.
