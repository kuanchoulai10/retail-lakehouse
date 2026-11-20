# Maintenance Policy Target State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A maintenance policy says only when a table is checked (`on.schedule`, optional `on.catalog_commit` with a debounce) and what state the table should be in (one optional block per operation with its `target` and optional `options`); cooldowns and back-off move to platform settings, the reconciliation follows `on:`, and the console edits and shows the new shape.

**Architecture:** `MaintenancePolicyContent` becomes `description`, `on` (`MaintenanceTriggers`), `dry_run` and four optional `OperationSpec[Target, Options]` blocks; an absent block means the operation is not done. `assess_maintenance` compares each target (`at_most` means due when over it) and takes cooldowns from a platform `OperationCooldowns`. The plan hands the workflow `schedule_interval_seconds` and `catalog_commit_debounce_seconds`; the reconciliation workflow opens a commit window on the first unchecked commit and checks when it closes. A table that becomes managed gets its own `table_managed` signal and is checked at once; a discovery scan only makes sure the workflow exists.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK, PySpark runtime (Iceberg 1.10.1 procedures), Helm, React + TanStack Query + orval + MSW, Storybook/vitest.

**Spec:** Linear KCL-91 (https://linear.app/kcl10/issue/KCL-91, no comments), `docs/adr/0012-policies-on-the-catalog-hierarchy.md` section "Maintenance policy", the KCL-83 discussion it settles, and KCL-89 (priority on the table). KCL-93 has landed (HEAD `6c8b7ae7`, plan `docs/superpowers/plans/2026-11-20-per-table-maintenance-workflow.md`): one maintenance workflow per table, no rounds, candidates, admission or scheduler settings, whole-table `rewrite_data_files`, queued attempts and a queue wait limit; the policy's `priority` is read by nothing.

## Global Constraints

Decisions this plan makes are marked **(decided)** with the reason; the rest is copied from the issue and ADR 0012.

- **Wire shape (decided: the ADR's YAML, which puts the blocks beside `on:`).** Create and update bodies, and every policy response, carry `description`, `on`, `dry_run` and the four optional blocks at the top level; there is no `operations` wrapper, no `priority`, no `reconcile_interval_seconds`, no `cooldown_seconds`, no `enabled`, no `trigger_policy` / `execution_policy` / `conditions` / `scope`:
  ```json
  {"description": "Platform default",
   "on": {"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": 300}},
   "dry_run": false,
   "rewrite_data_files": {"target": {"reducible_files": {"at_most": 5}, "per": "partition"},
                          "options": {"min_input_files": 2, "partial_progress_enabled": true}},
   "rewrite_manifests":  {"target": {"small_manifests": {"at_most": 5}}, "options": null},
   "expire_snapshots":   {"target": {"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400}, "options": null},
   "remove_orphan_files": {"target": {"older_than_seconds": 259200}, "options": null}}
  ```
  This is exactly the platform default policy's content (`mp-00000000000000000000000000`, name `default`). A block that is absent or `null` means the operation is not done; a policy may hold no block at all. `dry_run` defaults to `false`.
- **Durations are whole seconds with a `_seconds` name on the wire (decided: every other duration in this API is, and `WholeSeconds` already does it).** The domain holds `timedelta`; the alias carries the wire name.
- **`on:` limits (decided).** `on.schedule` is required, `every_seconds` from `60` to `604800` (1 minute to 7 days: the floor bounds catalog reads per table, the ceiling keeps "a table whose events are lost is still checked" meaningful). `on.catalog_commit` is optional; `debounce_seconds` from `0` to `86400`, default `300`. Leaving `catalog_commit` out means commits do not trigger a check.
- **Debounce semantics (decided: a resetting debounce never fires on a table written every minute, which is exactly the CDC table that needs checks; this is lodash's `maxWait = wait`).** The first commit not yet covered by a check opens a window of `debounce`; commits inside it join it and do not move its end; the check runs when it closes, recording `catalog_commit: <commits in the window>`. A check for any other reason before the window closes takes the window with it (its commits are counted in that check's wake reasons). A window that closes while a run is in flight is counted and checked after the run, like every other wake.
- **A commit with no `catalog_commit` in the policy plans nothing and counts nothing**, but still cancels a pending `stop` (R31: it comes from a hint that read the table as managed).
- **Before its first plan a reconciliation workflow assumes the platform default** (`schedule_interval_seconds` 3600, `catalog_commit_debounce_seconds` 300); every plan replaces both with the applied policy's values (`None` debounce when the policy has no `catalog_commit`).
- **Always a check, never in `on:` (ADR):** a manual run, Reconcile now, a policy change (already: `notify_policy_change` sends `policy_changed`), and a table becoming managed. **(decided)** "Becoming managed" is a new table change `managed` → signal `table_managed` → wake reason `table_managed`, sent by discovery and by the catalog event path whenever a registration or a known table ends up managed. A discovery scan of an already managed table still sends `seen` (signal-with-start keeps a lost workflow alive) but `table_seen` no longer counts a reason or plans; the wake reason `discovery_scan` is removed from `WakeReason` and the console.
- **Targets (ADR).** `rewrite_data_files.target`: `reducible_files.at_most` (≥ 0) and `per` (`partition` default, or `table`). `rewrite_manifests.target`: `small_manifests.at_most` (≥ 0), "small" = under the table's `commit.manifest.target-size-bytes`, else 8 MiB (`smaller_than_bytes` is gone). `expire_snapshots.target`: `min_snapshots_to_keep` (≥ 1) and `max_snapshot_age_seconds` (> 0). `remove_orphan_files.target`: `older_than_seconds` (≥ 86400). The target file size is the table's `write.target-file-size-bytes` (else 512 MiB); the policy holds none.
- **Comparison (decided: keep `Measurement.met` meaning "due", so records, health and the console read as before).** An `at_most` target is measured with `threshold = at_most`, comparison `MORE_THAN` (`>`): `met` (due) when the observed count is over the target. With `per: partition` every partition is compared on its own; `reducible_files` is the sum over the partitions over the target and `qualifying_partitions` counts them; with `per: table` the table's total is compared. Snapshot expiry is due when `expirable_snapshots > 0`. Measurement keys stay `reducible_files`, `target_file_size`, `qualifying_partitions`, `small_manifests`, `expirable_snapshots`.
- **Snapshot retention (decided: the ADR says the policy wins where it overlaps `history.expire.*`, which also means the table property applies where the policy is silent).** Each of the two values is the policy's, else the table property (`history.expire.min-snapshots-to-keep`; `history.expire.max-snapshot-age-ms`, in milliseconds), else Iceberg's default (1 snapshot, 5 days). The resolved values are both measured and passed to the procedure, so the check and the run agree.
- **Options (decided: a typed, curated subset of each Iceberg 1.10.1 procedure, so types are checked, OpenAPI documents them and the runtime renders no free-form SQL; another argument is one more field).** Unknown keys are refused (422 from the API, `InvariantViolation` in the domain), which also refuses every value `target` or the platform owns: there is no option for `where`, `target_file_size_bytes` / `target-file-size-bytes`, `older_than`, `retain_last`, `dry_run` or `location`. An unset option is left to the procedure.
  - `rewrite_data_files`: `strategy` (`binpack` | `sort`), `sort_order` (non-empty, ≤ 1000 characters, only with `strategy: sort`), `min_input_files`, `partial_progress_enabled`, `partial_progress_max_commits` (only with `partial_progress_enabled: true`), `max_concurrent_file_group_rewrites`, `rewrite_all`, `delete_file_threshold`, `remove_dangling_deletes`, `max_file_group_size_bytes`. Integers are positive.
  - `rewrite_manifests`: `use_caching`.
  - `expire_snapshots`: `max_concurrent_deletes`, `stream_results`.
  - `remove_orphan_files`: `max_concurrent_deletes`, `prefix_mismatch_mode` (`ERROR` | `IGNORE` | `DELETE`).
- **Procedure arguments handed to the Spark runtime (decided).** `procedure_args` per operation, only set keys present:
  - `rewrite_data_files`: `{"strategy"?, "sort_order"?, "options": {"target-file-size-bytes": <resolved>, "min-input-files"?, "partial-progress.enabled"?, "partial-progress.max-commits"?, "max-concurrent-file-group-rewrites"?, "rewrite-all"?, "delete-file-threshold"?, "remove-dangling-deletes"?, "max-file-group-size-bytes"?}}`
  - `rewrite_manifests`: `{"use_caching"?}`
  - `expire_snapshots`: `{"older_than": <ISO-8601 UTC>, "retain_last": <int>, "max_concurrent_deletes"?, "stream_results"?}`
  - `remove_orphan_files`: `{"older_than": <ISO-8601 UTC>, "max_concurrent_deletes"?, "prefix_mismatch_mode"?}` (the runtime keeps adding `prefix_listing => true`)
  The runtime refuses a key it does not know for the operation (`ValueError`), so drift fails loudly instead of dropping a user's option.
- **A manual run of an operation the policy leaves out (decided: "what is not written, the platform decides").** It runs with no options: `rewrite_data_files` gets only the resolved target file size, `rewrite_manifests` nothing, `expire_snapshots` the retention resolved from the table's properties and Iceberg's defaults, `remove_orphan_files` `older_than` = now − 3 days (Iceberg's own default).
- **`dry_run` keeps its meaning:** a scheduled plan records what would run and starts nothing; a manual run still runs.
- **Cooldowns and back-off are platform settings (ADR).** Exact names and defaults: `GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS` `3600`, `GLAC_MAINTENANCE_REWRITE_MANIFESTS_COOLDOWN_SECONDS` `21600`, `GLAC_MAINTENANCE_EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS` `21600` (each ≥ 0), `GLAC_MAINTENANCE_REMOVE_ORPHAN_FILES_INTERVAL_SECONDS` `604800` (≥ 1; orphan files have no cheap target, so they are due on this interval); chart `worker.rewriteDataFilesCooldownSeconds`, `worker.rewriteManifestsCooldownSeconds`, `worker.expireSnapshotsCooldownSeconds`, `worker.removeOrphanFilesIntervalSeconds`. The failure back-off (`GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS`, doubling per consecutive failure) is unchanged and now doubles the platform cooldown.
- **Plan and workflow names (decided: "reconcile interval" leaves the vocabulary with the field).** `PlanTableMaintenanceUseCaseOutput.reconcile_interval_seconds` becomes `schedule_interval_seconds`, plus `catalog_commit_debounce_seconds: int | None`; `TableReconciliationWorkflowInput.reconcile_interval_seconds` becomes `schedule_interval_seconds`, and the `state` query key likewise.
- **Removed:** `MaintenancePriority` and the policy's `priority` (API type `MaintenancePriorityApi`), `TriggerPolicy`, `OperationPolicy`, `OperationPolicies`, every `*_policy.py` / `*_trigger_policy.py` / `*_conditions.py` / `*_execution_policy.py` of the four operations, `AtLeast`, `CompactionScope`, `PartialProgress`, `SmallManifestsCondition`, `resolve_execution_target_file_size`, `SizeSource.CONDITION`; on the console `PriorityText.tsx`, `lib/priorityText.ts` and its test (only policy pages use them). `CompactionUnit` stays (it is `per`).
- **No data migration and no new `workflow.patched` markers:** policies stored in the old shape do not load and running workflows carry the old input; the cluster is rebuilt before deploy (`task offboard`, `task onboard KUBE_CONTEXT=retail-lakehouse`), and the default policy is seeded in the new shape by the migration.
- **Tasks 3 and 4 share one commit (decided):** Task 3 changes the API contract, so the regenerated client and the console that compiles against it land together; Task 3 ends with the backend suite green and no commit.
- **Boundaries with the issues built on top (state them, do not build them):**
  - KCL-94 builds partition selection: `where` clauses from the partitions over the target, at most N per job, quiet period and maximum wait (three platform settings), and the run recording its `where`. Here `per` only decides whether `rewrite_data_files` is due; a run still compacts the whole table (KCL-93), `assess_maintenance` still lists the qualifying partitions that the plan ignores, and `build_partition_filters` is untouched.
  - KCL-95 makes a run one operation and moves the Maintenance, Reconciliations and Commits tabs to side panels; nothing here touches the run model, its API or those tabs.
  - KCL-98 builds `effective-policies`, the per-target policy panel and the `mappings` → `attachments` rename; here the `applicable-policy` responses only change their content fields to the new shape, and `ApplicablePolicyPanel` keeps working.
  - KCL-71 (plan `docs/superpowers/plans/2026-11-20-discovery-policy.md`) rewrites discovery onto discovery policies and may land before or after this plan; Task 7 changes only which table change `register_discovered_table` and `apply_discovery_to_known_table` send, and is written so it applies to either version of those helpers (their rules argument is a discovery policy after KCL-71).
- Follow `CLAUDE.md`: TDD; one object per file; `from __future__ import annotations`; StrEnum; ABC ports; `uv run`, never bare `python` / `pytest`; never `cd`; kubectl verb first, then flags; never `--no-verify`; never `sops`; never edit `.claude/settings*.json`; do not touch `platform/30-thanos`, `platform/24-e2e-validation`, the ArgoCD path or `.claude/worktrees/`; no comments in `values.yaml`.
- `<pytest>` below means `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`; `<spark-pytest>` means `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/runtime/spark --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/runtime/spark pytest`; `<vitest>` means `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run`. Never run two suites at once.
- Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=<backend|frontend|all>`; a commit that changes `openapi.json` regenerates the client with `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`, commits it with the backend change and runs `scope=all`. `git add` names explicit paths. Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- A table written every minute with a 5-minute debounce is still checked every 5 minutes, not starved by a window that keeps moving; 30 commits in one window make one check that records `catalog_commit: 30` (Task 6).
- A commit window open at continue-as-new survives it with its end and its count, and closes on time in the new run (Task 6).
- A manual run of an operation whose block the policy leaves out builds its procedure arguments from the table's properties and Iceberg's defaults instead of failing on a missing block (Task 3).
- An `expire_snapshots` target that sets only `max_snapshot_age_seconds` keeps `history.expire.min-snapshots-to-keep` from the table; a table property in milliseconds (`history.expire.max-snapshot-age-ms: 172800000`) reads as 2 days, a malformed one falls back to Iceberg's 5 days; the measurement and the procedure arguments use the same values (Task 3).
- An option that repeats a target value (`expire_snapshots.options.retain_last`, `rewrite_data_files.options.target_file_size_bytes`) is refused with 422 on create and update, never stored and ignored (Tasks 1 and 3).

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `TM` = `context/table_maintenance`; `POLICY` = `TM/application/domain/model/table_maintenance_policy`; `TEMPORAL` = `TM/adapter/hybrid/temporal`; tests mirror under `tests/`. Frontend paths are relative to `src/data-platform/frontend/src/`.

| File | Responsibility |
|---|---|
| `POLICY/{schedule_trigger,catalog_commit_trigger,maintenance_triggers}.py` (new) | `on:` |
| `POLICY/{at_most,rewrite_data_files_target,rewrite_data_files_options,rewrite_data_files_strategy,rewrite_manifests_target,rewrite_manifests_options,expire_snapshots_target,expire_snapshots_options,remove_orphan_files_target,remove_orphan_files_options,prefix_mismatch_mode}.py` (new) | targets and options |
| `POLICY/{operation_spec,rewrite_data_files_spec,rewrite_manifests_spec,expire_snapshots_spec,remove_orphan_files_spec}.py` (new) | one block per operation |
| `POLICY/maintenance_policy_content.py` | the new content and the platform default |
| `TM/application/domain/model/table/operation_cooldowns.py` (new) | platform cooldowns and back-off cap |
| `TM/application/domain/model/shared/{snapshot_retention,platform_settings,size_source}.py` | resolved retention; cooldown settings; no `CONDITION` |
| `TM/application/domain/service/shared/resolve_snapshot_retention.py` (new) | policy, else table property, else Iceberg default |
| `TM/application/domain/service/table/assess_maintenance.py` | targets and platform cooldowns |
| `TM/application/service/table_maintenance_run/maintenance_procedure_args.py` | procedure arguments from targets and options |
| `TM/application/service/table/{plan_table_maintenance,get_table_health}.py`, `TM/application/port/inbound/table/plan_table_maintenance/output.py` | schedule and debounce out, cooldowns in |
| `TM/adapter/inbound/web/table_maintenance_policy/dto.py`, `TM/adapter/inbound/web/table_maintenance_policy_attachment/dto.py` | API shape |
| `bootstrap/configs/app_settings.py`, `bootstrap/container/{build_operation_cooldowns (new),build_platform_settings,build_use_cases,build_connected_use_cases}.py` | settings and wiring |
| `TM/application/service/table_maintenance_run/get_platform_settings.py` | cooldowns on the Platform settings page |
| `src/data-platform/runtime/spark/sql_builder.py` | renders the new procedure arguments |
| `TEMPORAL/contracts/table_reconciliation/{workflow_input,signal}.py`, `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py` | schedule, commit window, `table_managed` |
| `TM/application/domain/model/table/table_change.py`, `TM/application/domain/model/table_reconciliation/wake_reason.py`, `TM/application/service/table/{register_discovered_table,apply_discovery_to_known_table,process_table_hint,sync_discovered_tables}.py`, `TEMPORAL/outbound/table/send_table_change_temporal_gateway.py` | becoming managed is its own change |
| `lib/policyDraft.ts`, `lib/policyChecksText.ts` (new), `components/{PolicyEditor,OperationPolicySection,PolicySummary}.tsx`, `pages/{PoliciesPage,PolicyVersionPage}.tsx`, `components/tabs/reconciliationText.ts`, `test/fixtures.ts`, `stories/storyData.ts` | console |
| `platform/25-lakehouse-control-plane/chart/{values.yaml,templates/configmap.yaml}`, `e2e.sh`, `README.md` | chart, e2e, docs |

---

### Task 1: Target-state value objects

New files only; the old content classes stay until Task 3, so nothing else changes.

**Files:**
- Create: under `POLICY/`: `schedule_trigger.py`, `catalog_commit_trigger.py`, `maintenance_triggers.py`, `at_most.py`, `rewrite_data_files_strategy.py`, `rewrite_data_files_target.py`, `rewrite_data_files_options.py`, `rewrite_manifests_target.py`, `rewrite_manifests_options.py`, `expire_snapshots_target.py`, `expire_snapshots_options.py`, `remove_orphan_files_target.py`, `prefix_mismatch_mode.py`, `remove_orphan_files_options.py`, `operation_spec.py`, `rewrite_data_files_spec.py`, `rewrite_manifests_spec.py`, `expire_snapshots_spec.py`, `remove_orphan_files_spec.py`; export all from `POLICY/__init__.py`
- Test: new `tests/context/table_maintenance/application/domain/model/table_maintenance_policy/test_maintenance_triggers.py`, `test_operation_targets.py`, `test_operation_options.py`

**Interfaces:**
- Produces (all `ValueObject`, so frozen, strict and `extra="forbid"`):
  - `ScheduleTrigger(every: WholeSeconds)`, wire `every_seconds`; `60 s ≤ every ≤ 7 days`, else "must be between 60 and 604800 seconds".
  - `CatalogCommitTrigger(debounce: WholeSeconds = timedelta(minutes=5))`, wire `debounce_seconds`; `0 ≤ debounce ≤ 1 day`.
  - `MaintenanceTriggers(schedule: ScheduleTrigger, catalog_commit: CatalogCommitTrigger | None = None)`.
  - `AtMost(at_most: NonNegativeInt)`.
  - `RewriteDataFilesStrategy(StrEnum)`: `BINPACK = "binpack"`, `SORT = "sort"`. `PrefixMismatchMode(StrEnum)`: `ERROR`, `IGNORE`, `DELETE` (values equal names).
  - `RewriteDataFilesTarget(reducible_files: AtMost, per: CompactionUnit = CompactionUnit.PARTITION)`.
  - `RewriteDataFilesOptions` with the fields of Global Constraints, all `| None = None`; `procedure_arguments() -> dict[str, str]` (`strategy`, `sort_order` when set) and `procedure_options() -> dict[str, int | bool]` (the set ones, in Iceberg's spelling: `min-input-files`, `partial-progress.enabled`, `partial-progress.max-commits`, `max-concurrent-file-group-rewrites`, `rewrite-all`, `delete-file-threshold`, `remove-dangling-deletes`, `max-file-group-size-bytes`).
  - `RewriteManifestsTarget(small_manifests: AtMost)`; `RewriteManifestsOptions(use_caching: bool | None = None)` with `procedure_arguments() -> dict[str, bool]`.
  - `ExpireSnapshotsTarget(min_snapshots_to_keep: PositiveInt | None = None, max_snapshot_age: PositiveDuration | None = None)`, wire `max_snapshot_age_seconds`; `ExpireSnapshotsOptions(max_concurrent_deletes: PositiveInt | None = None, stream_results: bool | None = None)` with `procedure_arguments() -> dict[str, int | bool]`.
  - `RemoveOrphanFilesTarget(older_than: WholeSeconds)`, wire `older_than_seconds`, at least 1 day ("must be at least 1 day", as today); `RemoveOrphanFilesOptions(max_concurrent_deletes: PositiveInt | None = None, prefix_mismatch_mode: PrefixMismatchMode | None = None)` with `procedure_arguments() -> dict[str, int | str]`.
  - `class OperationSpec[T: ValueObject, O: ValueObject](ValueObject)`: `target: T`, `options: O | None = None`. Aliases `RewriteDataFilesSpec = OperationSpec[RewriteDataFilesTarget, RewriteDataFilesOptions]` and the same for the other three.

- [ ] **Step 1: Write the failing tests**

```python
def test_schedule_reads_every_seconds():
    assert ScheduleTrigger.from_primitives({"every_seconds": 300}).every == timedelta(minutes=5)

@pytest.mark.parametrize("seconds", [0, 59, 604801])
def test_schedule_out_of_range_is_refused(seconds): ...       # InvariantViolation

def test_schedule_is_required():
    with pytest.raises(InvariantViolation):
        MaintenanceTriggers.from_primitives({"catalog_commit": {"debounce_seconds": 60}})

def test_catalog_commit_defaults_to_five_minutes():
    assert MaintenanceTriggers.from_primitives(
        {"schedule": {"every_seconds": 3600}, "catalog_commit": {}}
    ).catalog_commit.debounce == timedelta(minutes=5)

def test_no_catalog_commit_means_none(): ...                  # {"schedule": {...}} → catalog_commit is None
def test_zero_debounce_is_allowed(): ...
def test_debounce_over_a_day_is_refused(): ...

def test_reducible_files_target_is_per_partition_by_default():
    target = RewriteDataFilesTarget.from_primitives({"reducible_files": {"at_most": 5}})
    assert target.per is CompactionUnit.PARTITION

def test_at_most_zero_is_allowed_and_negative_is_refused(): ...
def test_expire_target_fields_are_optional(): ...            # {} → both None
def test_orphan_older_than_under_a_day_is_refused(): ...      # 86399 → InvariantViolation

def test_rewrite_options_render_iceberg_spelling():
    options = RewriteDataFilesOptions(min_input_files=2, partial_progress_enabled=True, partial_progress_max_commits=3)
    assert options.procedure_options() == {
        "min-input-files": 2, "partial-progress.enabled": True, "partial-progress.max-commits": 3,
    }
    assert options.procedure_arguments() == {}

def test_sort_order_needs_the_sort_strategy(): ...            # sort_order without strategy=sort → InvariantViolation
def test_max_commits_needs_partial_progress(): ...           # max_commits with partial_progress_enabled None → refused

@pytest.mark.parametrize(("options_type", "key"), [
    (RewriteDataFilesOptions, "target_file_size_bytes"), (RewriteDataFilesOptions, "where"),
    (ExpireSnapshotsOptions, "retain_last"), (ExpireSnapshotsOptions, "older_than"),
    (RemoveOrphanFilesOptions, "older_than"), (RemoveOrphanFilesOptions, "dry_run"),
    (RemoveOrphanFilesOptions, "location"),
])
def test_values_owned_by_the_target_or_platform_are_not_options(options_type, key):
    with pytest.raises(InvariantViolation):
        options_type.from_primitives({key: 1})

def test_unknown_prefix_mismatch_mode_is_refused(): ...
def test_a_spec_without_options_reads_none(): ...            # RewriteManifestsSpec.from_primitives({"target": {...}}).options is None
```

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table_maintenance_policy -v` → FAIL, the new names are not importable.
- [ ] **Step 3: Implement.** Bounds and cross-field rules are `field_validator` / `model_validator(mode="after")`; durations use `WholeSeconds` / `PositiveDuration` from the `shared` model, with `Field(validation_alias=..., serialization_alias=...)` as `ExpireSnapshotsExecutionPolicy` does today.
- [ ] **Step 4: Run them and watch them pass.**
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): add the target-state value objects of a maintenance policy (KCL-91)`.

### Task 2: Cooldowns come from platform settings

**Files:**
- Create: `TM/application/domain/model/table/operation_cooldowns.py` (export from `TM/application/domain/model/table/__init__.py`); `bootstrap/container/build_operation_cooldowns.py`
- Modify: `TM/application/domain/service/table/assess_maintenance.py`; `TM/application/service/table/plan_table_maintenance.py`, `get_table_health.py` (constructor kwarg `cooldowns` replaces `failure_backoff_cap`); `TM/application/domain/model/shared/platform_settings.py`; `TM/application/service/table_maintenance_run/get_platform_settings.py`; `bootstrap/configs/app_settings.py`; `bootstrap/container/build_platform_settings.py`, `build_use_cases.py`, `build_connected_use_cases.py`; chart `values.yaml` and `templates/configmap.yaml`; `stories/storyData.ts` (platform settings group `cooldown_and_backoff`)
- Test: new `tests/context/table_maintenance/application/domain/model/table/test_operation_cooldowns.py`; `test_assess_maintenance.py`, `test_assessment_plan.py`, `test_plan_table_maintenance_service.py`, `test_get_table_health.py`; `tests/bootstrap/configs/test_app_settings.py`, `tests/bootstrap/container/test_build_platform_settings.py`, `test_build_use_cases.py`; `test_get_platform_settings.py`

**Interfaces:**
- Produces:
  - `OperationCooldowns(rewrite_data_files: NonNegativeDuration, rewrite_manifests: NonNegativeDuration, expire_snapshots: NonNegativeDuration, remove_orphan_files: PositiveDuration, failure_backoff_cap: PositiveDuration)`; `for_operation(operation: MaintenanceOperation) -> timedelta`; `platform_default() -> OperationCooldowns` = 1 h, 6 h, 6 h, 7 d, cap `DEFAULT_FAILURE_BACKOFF_CAP` (24 h).
  - `assess_maintenance(table, policy, observation, now, *, cooldowns: OperationCooldowns = OperationCooldowns.platform_default())`; the eligible time is `last_attempt_at + state.effective_cooldown(cooldowns.for_operation(op), cooldowns.failure_backoff_cap)`; the policy's `trigger_policy.cooldown` is no longer read.
  - `PlanTableMaintenanceService(..., *, cooldowns: OperationCooldowns = ...)`, `GetTableHealthService(..., *, cooldowns: OperationCooldowns = ..., clock=...)`, `build_use_cases(..., cooldowns: OperationCooldowns = OperationCooldowns.platform_default())`; `build_operation_cooldowns(settings: AppSettings) -> OperationCooldowns`.
  - `AppSettings.maintenance_rewrite_data_files_cooldown_seconds: int = Field(default=3600, ge=0)`, `maintenance_rewrite_manifests_cooldown_seconds` (21600, ge 0), `maintenance_expire_snapshots_cooldown_seconds` (21600, ge 0), `maintenance_remove_orphan_files_interval_seconds` (604800, ge 1).
  - `PlatformSettings` gains `rewrite_data_files_cooldown_seconds`, `rewrite_manifests_cooldown_seconds`, `expire_snapshots_cooldown_seconds`, `remove_orphan_files_interval_seconds` (ints). The `cooldown_and_backoff` group lists, in this order, keys `maintenance_rewrite_data_files_cooldown_seconds` "Rewrite data files cooldown" ("The least time between two runs of rewrite data files on one table."), `maintenance_rewrite_manifests_cooldown_seconds` "Rewrite manifests cooldown" (same sentence with rewrite manifests), `maintenance_expire_snapshots_cooldown_seconds` "Expire snapshots cooldown" (same with expire snapshots), `maintenance_remove_orphan_files_interval_seconds` "Orphan file removal interval" ("How often orphan files are removed from a table: they have no target the platform can measure."), then the existing failure backoff cap, all unit `seconds`.
  - Chart `worker.rewriteDataFilesCooldownSeconds: 3600`, `worker.rewriteManifestsCooldownSeconds: 21600`, `worker.expireSnapshotsCooldownSeconds: 21600`, `worker.removeOrphanFilesIntervalSeconds: 604800`, rendered into the four `GLAC_MAINTENANCE_*` vars of Global Constraints.

- [ ] **Step 1: Write the failing tests**

```python
def test_platform_default_cooldowns():
    c = OperationCooldowns.platform_default()
    assert [c.for_operation(op) for op in MaintenanceOperation.ordered()] == [
        timedelta(hours=1), timedelta(hours=6), timedelta(hours=6), timedelta(days=7)]
    assert c.failure_backoff_cap == timedelta(hours=24)

def test_the_platform_cooldown_holds_an_operation_back(): ...   # last attempt 30 min ago, cooldown 1 h → COOLDOWN, next_eligible_at = last + 1 h
def test_a_policy_cooldown_of_zero_no_longer_frees_it(): ...    # policy cooldown_seconds 0, platform 1 h → still COOLDOWN
def test_failures_double_the_platform_cooldown_up_to_the_cap(): # 2 failures, 1 h → 4 h; 10 failures → cap
    ...
def test_orphan_files_are_due_on_the_platform_interval(): ...   # last 8 days ago, interval 7 d → DUE; 6 days → COOLDOWN
def test_app_settings_read_the_cooldown_env(monkeypatch): ...   # GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS=60 → 60
def test_negative_cooldown_is_refused(monkeypatch): ...         # ValidationError
def test_platform_settings_list_the_cooldowns(): ...            # group cooldown_and_backoff keys in the order above
def test_health_and_plan_use_the_injected_cooldowns(): ...      # plan with cooldowns rewrite 0 → due right after an attempt
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain tests/bootstrap -k "cooldown or platform_settings" -v`
- [ ] **Step 3: Implement.** `build_connected_use_cases` passes `cooldowns=build_operation_cooldowns(settings)`; update every existing test that tuned the cooldown through the policy to pass `cooldowns=` instead; update `storyData.ts` to the five items.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`; `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c "COOLDOWN_SECONDS\|INTERVAL_SECONDS"` shows the new vars.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): take maintenance cooldowns from platform settings (KCL-91)`.

### Task 3: The policy content is target state (backend)

**Files:**
- Create: `TM/application/domain/model/shared/snapshot_retention.py`; `TM/application/domain/service/shared/resolve_snapshot_retention.py`; `tests/context/table_maintenance/application/service/table_maintenance_run/test_maintenance_procedure_args.py`; `tests/context/table_maintenance/application/domain/service/shared/test_resolve_snapshot_retention.py`
- Modify: `POLICY/maintenance_policy_content.py`, `POLICY/__init__.py`; `TM/application/domain/service/table/assess_maintenance.py`; `TM/application/domain/model/shared/size_source.py`; `TM/application/service/table_maintenance_run/maintenance_procedure_args.py`; `TM/application/service/table/plan_table_maintenance.py` (docstring and the `_interval` source); `TM/adapter/inbound/web/table_maintenance_policy/dto.py`, `__init__.py`; `TM/adapter/inbound/web/table_maintenance_policy_attachment/dto.py` (`ApplicableTableMaintenancePolicyApiResponse`); `openapi.json` and the generated client (`task dev:generate-api`); `tests/context/table_maintenance/fakes/policy_with_operation.py`, `policy_with_only_operation.py`; every test in the "users" list below
- Delete: the classes listed under "Removed" in Global Constraints and their tests (`test_conditions.py`); `TM/application/domain/service/shared/resolve_execution_target_file_size.py`
- Test (users to update): `rg -l "MaintenancePolicyContent|OperationPolicies|trigger_policy|execution_policy|reconcile_interval|MaintenancePriority|policy_with_operation" src/data-platform/backend/tests` — the policy model, routes, SQL repo, attachment, assess, plan, health, run, reconciliation, activity and workflow-fake tests

**Interfaces:**
- Consumes: Task 1 (every value object), Task 2 (`OperationCooldowns`).
- Produces:
  - `MaintenancePolicyContent(description: str, on: MaintenanceTriggers, dry_run: bool = False, rewrite_data_files: RewriteDataFilesSpec | None = None, rewrite_manifests: RewriteManifestsSpec | None = None, expire_snapshots: ExpireSnapshotsSpec | None = None, remove_orphan_files: RemoveOrphanFilesSpec | None = None)`; `spec_for(operation: MaintenanceOperation) -> RewriteDataFilesSpec | RewriteManifestsSpec | ExpireSnapshotsSpec | RemoveOrphanFilesSpec | None`; `platform_default()` = the JSON in Global Constraints.
  - `SnapshotRetention(min_snapshots_to_keep: PositiveInt, max_snapshot_age: PositiveDuration)`; `resolve_snapshot_retention(target: ExpireSnapshotsTarget | None, properties: dict[str, str]) -> SnapshotRetention` (`positive_int_property` reads the two `history.expire.*` keys; the age property is milliseconds, floored to whole seconds, and a value under one second is ignored).
  - `assess_maintenance`: an absent spec → `DISABLED`; `rewrite_data_files`, `rewrite_manifests` and `expire_snapshots` are `DUE` when their deciding measurement is `met` (comparison `MORE_THAN`, thresholds `at_most`, `at_most`, `0`); `remove_orphan_files` is `DUE` whenever its block exists (the platform interval of Task 2 holds it back); `OperationAssessment.threshold` is the target's `at_most` (`0` for snapshots, `None` for orphans). `SizeSource` loses `CONDITION`.
  - `maintenance_procedure_args(operation, policy, properties, now) -> dict[str, Any]` returns the shapes of Global Constraints, including the absent-block rule.
  - DTOs (each `extra="forbid"`, request models also used in responses, as today): `ScheduleTriggerApiRequest(every_seconds: int)`, `CatalogCommitTriggerApiRequest(debounce_seconds: int = 300)`, `MaintenanceTriggersApiRequest(schedule, catalog_commit: ... | None = None)`, `AtMostApiRequest(at_most: int)`, `RewriteDataFilesTargetApiRequest(reducible_files, per: Literal["partition", "table"] = "partition")`, `RewriteDataFilesOptionsApiRequest` (the ten options, `strategy: Literal["binpack", "sort"] | None`), `RewriteManifestsTargetApiRequest`, `RewriteManifestsOptionsApiRequest`, `ExpireSnapshotsTargetApiRequest(min_snapshots_to_keep: int | None = None, max_snapshot_age_seconds: int | None = None)`, `ExpireSnapshotsOptionsApiRequest`, `RemoveOrphanFilesTargetApiRequest(older_than_seconds: int)`, `RemoveOrphanFilesOptionsApiRequest(prefix_mismatch_mode: Literal["ERROR", "IGNORE", "DELETE"] | None = None, ...)`, `RewriteDataFilesSpecApiRequest(target, options: ... | None = None)` and the other three specs. `CreateTableMaintenancePolicyApiRequest`, `UpdateTableMaintenancePolicyApiRequest`, `TableMaintenancePolicyApiResponse`, `ListedTableMaintenancePolicyApiResponse`, `TableMaintenancePolicyVersionApiResponse` and `ApplicableTableMaintenancePolicyApiResponse` carry `description`, `on: MaintenanceTriggersApiRequest`, `dry_run: bool` (default `False` on requests) and the four optional specs; `MaintenancePriorityApi` and `OperationPoliciesApiRequest` are gone. The Python attribute is `on` (no alias needed).
  - The plan output keeps `reconcile_interval_seconds` in this task, filled from `on.schedule.every` (Task 6 renames it).

- [ ] **Step 1: Write the failing tests**

```python
def test_platform_default_is_the_documented_content():
    assert MaintenancePolicyContent.platform_default().to_primitives() == DEFAULT_CONTENT_JSON  # the Global Constraints JSON

def test_a_block_left_out_is_none(): ...                       # content without expire_snapshots → spec_for(EXPIRE_SNAPSHOTS) is None
def test_old_shape_is_refused(): ...                           # {"reconcile_interval_seconds": ..., "operations": ...} → InvariantViolation

def test_an_absent_block_is_disabled(): ...                    # verdict DISABLED, no measurements
def test_reducible_files_at_the_target_is_not_due(): ...        # per table, total 5, at_most 5 → NOT_DUE, measurement comparison ">"
def test_reducible_files_over_the_target_is_due(): ...          # total 6 → DUE
def test_per_partition_compares_each_partition(): ...          # partitions 3, 3 with at_most 5 → NOT_DUE although total 6
def test_per_partition_counts_the_partitions_over_target(): ... # 7, 1, 9 → reducible_files 16, qualifying_partitions 2, DUE
def test_small_manifests_use_the_table_property(): ...          # commit.manifest.target-size-bytes 1024 → size_source TABLE_PROPERTY
def test_expirable_snapshots_over_zero_are_due(): ...
def test_orphan_files_are_due_when_their_block_exists(): ...

def test_retention_policy_wins(): ...                           # target 10 / 1 d, properties 3 / 2 d → 10, 1 d
def test_retention_falls_back_to_the_table(): ...               # target {max_snapshot_age: 1 d}, min property "3" → 3, 1 d
def test_retention_reads_milliseconds(): ...                    # history.expire.max-snapshot-age-ms "172800000" → 2 d
def test_retention_ignores_a_malformed_property(): ...          # "abc" → 5 d
def test_retention_without_a_block_is_icebergs_default(): ...   # None, {} → 1, 5 d
def test_assessment_and_args_agree_on_retention(): ...          # target {max_snapshot_age: 1 d}, property min "3": assess counts past the newest 3, args retain_last 3

def test_rewrite_args_carry_the_options_map():
    args = maintenance_procedure_args(REWRITE_DATA_FILES, MaintenancePolicyContent.platform_default(), {}, NOW)
    assert args == {"options": {"target-file-size-bytes": 536870912, "min-input-files": 2, "partial-progress.enabled": True}}

def test_rewrite_args_with_sort_strategy(): ...                 # strategy sort + sort_order "id DESC" → top-level keys
def test_expire_args_use_the_resolved_retention(): ...          # older_than == (NOW - 1 d).isoformat(), retain_last 10
def test_args_of_an_absent_block_use_defaults(): ...            # expire: properties min 3 → retain_last 3, older_than NOW - 5 d; orphans NOW - 3 d; manifests {}
def test_orphan_args_carry_prefix_mismatch_mode(): ...

def test_create_accepts_the_new_shape(client): ...              # POST with DEFAULT_CONTENT_JSON + name → 201, body round-trips
def test_create_refuses_an_option_that_repeats_the_target(client): ...  # expire_snapshots.options.retain_last → 422
def test_update_refuses_an_option_that_repeats_the_target(client): ...  # rewrite_data_files.options.target_file_size_bytes → 422, version unchanged
def test_create_refuses_the_old_fields(client): ...             # priority / reconcile_interval_seconds / operations → 422
def test_update_without_a_block_removes_it(client): ...         # PUT without remove_orphan_files → GET shows null
def test_applicable_policy_shows_the_new_shape(client): ...     # GET /v1/tables/{uuid}/applicable-policy → "on", no "operations"
def test_sql_round_trip_keeps_every_block(): ...                # repo test, content_json read back equal
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application tests/context/table_maintenance/adapter/inbound/web/table_maintenance_policy -v` → FAIL.
- [ ] **Step 3: Implement.** Rewrite `policy_with_operation(content, operation, spec)` to replace one block (`None` removes it) and `policy_with_only_operation` to drop the other blocks; fix every test the "users" `rg` lists; delete the removed classes; then `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`, then `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend lint-imports` and the same `uv run ... ty check`. Do not commit: the console does not compile against the new client until Task 4.

### Task 4: The console edits and shows target-state policies

**Files:**
- Create: `lib/policyChecksText.ts` with `policyChecksText.test.ts`
- Modify: `lib/policyDraft.ts` (+ its test if present, else create `lib/policyDraft.test.ts`); `components/PolicyEditor.tsx` (+ test, stories); `components/OperationPolicySection.tsx` (+ test, stories); `components/PolicySummary.tsx`; `pages/PoliciesPage.tsx` (+ test, stories); `pages/PolicyVersionPage.tsx` (+ test, stories); `components/tabs/reconciliationText.ts` (+ test); `test/fixtures.ts`; `stories/storyData.ts`, `stories/lakehouseHandlers.ts` if they build policies
- Delete: `components/PriorityText.tsx`, `lib/priorityText.ts`, `lib/priorityText.test.ts`

**Interfaces:**
- Consumes: the generated client of Task 3 (`CreateTableMaintenancePolicyApiRequest`, `MaintenanceTriggersApiRequest`, the four `*SpecApiRequest` types).
- Produces:
  - `PolicyContent = Omit<CreateTableMaintenancePolicyApiRequest, "name">`. `PolicyDraft` holds text fields: `description`, `scheduleEvery`, `catalogCommit: boolean`, `debounce`, `dryRun`, and per operation `included: boolean` plus its target and option fields as strings (optional booleans as `"" | "true" | "false"`, strategy as `"" | "binpack" | "sort"`). `draftFromContent(content)`; `contentFromDraft(draft) -> {content} | {error}`: an excluded operation is sent as `null`, an empty option is left out, `catalog_commit` is `null` when off; messages name the section and field ("Expire snapshots: Min snapshots to keep must be a whole number."), and `Check every` must be 60 to 604800 seconds.
  - `policyChecksText(on: MaintenanceTriggersApiRequest): string`: `"Every 1 h"` / `"Every 1 h, and 5 min after a commit"` / `"Every 5 min, and right after a commit"` (debounce 0), with `formatSeconds`.
  - `OperationPolicySection` props: `title`, `included`, `onIncludedChange`, `target: ReactNode`, `options: ReactNode`; the switch reads "In this policy"; when off it shows "Not in this policy: this operation does not run on a schedule." and hides the groups; groups are legend "Target" and "Options" (hint "Empty: the procedure's default.").
  - `PolicyEditor`: Description; "Check every (seconds)"; switch "Check after catalog commits" with "Debounce (seconds)" (hint "The check runs this long after the first commit; later commits join it"); Dry run; the four sections; a line "Cooldowns and failure back-off are platform settings." linking to the Platform settings page. No priority field. Optional booleans are a `SelectField` with "Procedure default", "On", "Off".
  - `PolicySummary` props `{content: PolicyContent}`: a Policy panel (Description, Checks = `policyChecksText`, Dry run) and one panel per operation, either "Not in this policy" or its target facts ("Reducible files at most 5, per partition"; "Small manifests at most 5"; "Keep at least 10 snapshots", "Expire snapshots older than 1 d" or "The table's history.expire.* / Iceberg default" when unset; "Remove orphan files older than 3 d") and the options it sets ("Procedure defaults" when none).
  - `PoliciesPage`: the Priority column becomes "Checks" (`policyChecksText`). `reconciliationText`: `off` reads "Not in the policy.", and a due operation with no deciding measurement reads "Due on the platform's interval."

- [ ] **Step 1: Write the failing tests and stories:** `policyDraft` round trip of the default content; an excluded operation becomes `null` and comes back excluded with its last values kept in the draft; `Check every` `30` → error; empty option left out; `policyChecksText` three cases; `PolicyEditor` creates a policy whose POST body (MSW call log) has `on.catalog_commit: null` when the switch is off and no `priority`; turning "In this policy" off for Expire snapshots sends `expire_snapshots: null`; a 422 detail shows in the dialog; keyboard: Tab reaches Check every, Space toggles "Check after catalog commits" and "In this policy" (the section's fields disappear and reappear), Escape closes; `PolicyVersionPage` shows "Not in this policy" for an absent block; `PoliciesPage` shows the Checks column. Stories: editor for the default policy, a policy without catalog commits, one with only rewrite data files; version page of each.
- [ ] **Step 2: Run and watch them fail:** `<vitest> policyDraft policyChecksText PolicyEditor OperationPolicySection PoliciesPage PolicyVersionPage reconciliationText`
- [ ] **Step 3: Implement** with design-system parts only (`Switch`, `TextField`, `Panel`, the console's `WholeNumberField`, `SelectField`, `CheckboxField`), per `src/data-platform/frontend/CLAUDE.md`.
- [ ] **Step 4: Run and watch them pass**, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit Tasks 3 and 4 together.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): make a maintenance policy describe the table's target state (KCL-91)` with the backend, `openapi.json`, the generated client and the console.

### Task 5: The Spark runtime renders the new procedure arguments

**Files:**
- Modify: `src/data-platform/runtime/spark/sql_builder.py`; `src/data-platform/runtime/spark/README.md` (the arguments it accepts)
- Test: `src/data-platform/runtime/spark/tests/test_sql_builder.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: the `procedure_args` shapes of Global Constraints (produced by Task 3).
- Produces: `build_call_statements(request) -> list[str]` unchanged in signature. Per operation it renders, in this order after `table => …`: `rewrite_data_files` `strategy => 'binpack'`, `sort_order => '<literal>'`, `options => map(...)` from `procedure_args["options"]` (omitted when empty); `rewrite_manifests` `use_caching => true|false`; `expire_snapshots` `older_than`, `retain_last`, `max_concurrent_deletes => N`, `stream_results => true|false`; `remove_orphan_files` `older_than`, `prefix_listing => true`, `max_concurrent_deletes => N`, `prefix_mismatch_mode => 'IGNORE'`; then `where` as today. A key outside these for the operation, a `strategy` outside `binpack`/`sort`, a `prefix_mismatch_mode` outside `ERROR`/`IGNORE`/`DELETE`, a non-bool where a bool belongs or a non-positive int raises `ValueError`.

- [ ] **Step 1: Write the failing tests**

```python
def test_rewrite_data_files_renders_strategy_sort_order_and_options():
    (statement,) = build_call_statements(make_request(operation="rewrite_data_files", procedure_args={
        "strategy": "sort", "sort_order": "id DESC NULLS LAST",
        "options": {"target-file-size-bytes": 536870912, "min-input-files": 2}}))
    assert "strategy => 'sort', sort_order => 'id DESC NULLS LAST', options => map('target-file-size-bytes', '536870912', 'min-input-files', '2')" in statement

def test_rewrite_manifests_renders_use_caching(): ...         # "use_caching => false"
def test_expire_snapshots_renders_its_options(): ...          # max_concurrent_deletes => 4, stream_results => true
def test_remove_orphan_files_renders_prefix_mismatch_mode(): ...
def test_an_unknown_argument_is_refused(): ...                # expire_snapshots {"retain_last": 1, "older_than": ..., "foo": 1} → ValueError
def test_a_flat_rewrite_option_is_refused(): ...              # {"min-input-files": 2} at the top level → ValueError
def test_an_unknown_strategy_is_refused(): ...                # "zorder" → ValueError
def test_a_where_clause_still_makes_one_call_per_filter(): ...
```

- [ ] **Step 2: Run and watch them fail:** `<spark-pytest> tests/test_sql_builder.py -v`
- [ ] **Step 3: Implement** with one renderer per operation; string values go through `sql_literal`.
- [ ] **Step 4: Run and watch them pass:** `<spark-pytest> -q`
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(spark-runtime): pass a policy's procedure options to the Iceberg procedures (KCL-91)`.

### Task 6: The reconciliation follows `on.schedule` and debounces catalog commits

**Files:**
- Modify: `TM/application/port/inbound/table/plan_table_maintenance/output.py`; `TM/application/service/table/plan_table_maintenance.py`; `TEMPORAL/contracts/table_reconciliation/workflow_input.py`; `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py`
- Test: `test_plan_table_maintenance_service.py`; `tests/.../temporal/inbound/test_table_reconciliation_workflow.py`, `test_raise_during_the_run_report.py`, `use_case_fakes.py`, `test_activities.py`; `tests/.../temporal/contracts/test_temporal_contracts.py`

**Interfaces:**
- Consumes: Task 3 (`MaintenancePolicyContent.on`).
- Produces:
  - `PlanTableMaintenanceUseCaseOutput.schedule_interval_seconds: int` (replaces `reconcile_interval_seconds`) and `catalog_commit_debounce_seconds: int | None`, on planned and skip outputs alike; an unknown table answers the platform default's `3600` and `300`.
  - `TableReconciliationWorkflowInput`: `schedule_interval_seconds: int = 3600` (renamed), `catalog_commit_debounce_seconds: int | None = 300`, `commit_window_closes_at: str | None = None` (ISO-8601), `pending_commits: int = 0`; `_carry()` passes all four.
  - Workflow behaviour:
    - `table_updated`: with `self._commit_debounce is None` it only cancels `stop` and wakes without a reason; otherwise `pending_commits += 1`, opens the window at `now + debounce` when none is open (never moves an open one), cancels `stop` and wakes (so the wait re-arms its timer).
    - `_has_reason_to_plan`: a window whose end has passed adds `pending_commits` to `wake_reasons["catalog_commit"]` and closes.
    - `_plan_and_start_once`: before taking the reasons, an open window adds its commits to `catalog_commit` and closes (the plan covers them); after the plan, `self._interval` and `self._commit_debounce` come from `schedule_interval_seconds` and `catalog_commit_debounce_seconds`. A failed plan keeps both.
    - `_wait`: with no run in flight the timer is the earlier of `next_plan_at` and `commit_window_closes_at`; with a run in flight it stays the run's deadline.
    - `state()` reports `schedule_interval_seconds`, `catalog_commit_debounce_seconds`, `commit_window_closes_at`, `pending_commits` (and no `reconcile_interval_seconds`).

- [ ] **Step 1: Write the failing tests.** The harness's `_planned(..., interval=3600, debounce=300)` and `_skip(..., debounce=300)` now emit `schedule_interval_seconds` and `catalog_commit_debounce_seconds`.

```python
def test_the_plan_carries_the_schedule_and_the_debounce(): ...  # service: on every 600, catalog_commit 120 → 600, 120; no catalog_commit → None
def test_commits_inside_the_window_make_one_check():
    # plan with debounce 300; TABLE_UPDATED at t, t+60 s, t+120 s; no record before t+300 s;
    # one record at t+300 s with wake_reasons == {"catalog_commit": 3}
    ...
def test_a_table_written_every_minute_is_checked_every_window(): ...  # a commit every 60 s for 11 min → records at ~t+300 and ~t+600
def test_thirty_commits_in_one_window_record_thirty(): ...
def test_commits_are_ignored_without_catalog_commit(): ...      # debounce None; commit; sleep 3000 s → no record, wake_reasons {}
def test_a_commit_after_stop_cancels_it_without_catalog_commit(): ...  # STOP then TABLE_UPDATED → workflow still running
def test_another_check_takes_the_open_window(): ...            # commit, then RECONCILE_NOW → {"catalog_commit": 1, "reconcile_now": 1}; nothing at window end
def test_a_window_closing_during_a_run_is_checked_after_it(): ...  # → {"catalog_commit": 1, "previous_run_finished": 1}
def test_the_window_survives_continue_as_new(): ...            # continue_as_new_after=1; window end and count carried; record at the original end
def test_a_zero_debounce_checks_at_once(): ...
def test_the_first_plan_waits_the_default_debounce(): ...      # fresh workflow, TABLE_UPDATED as start signal → record after 300 s
def test_the_schedule_interval_comes_from_the_plan(): ...      # plan says 300 → next scheduled record 300 s later
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal -k "window or commit or schedule or debounce" -v`
- [ ] **Step 3: Implement;** rename `reconcile_interval_seconds` everywhere `rg -n reconcile_interval_seconds src/data-platform/backend` finds it.
- [ ] **Step 4: Run and watch them pass**, with `tests/architecture/test_temporal_workflow_determinism.py` and `test_temporal_workflow_sandbox.py`: `<pytest> -q`
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): check tables on the policy's schedule and debounce catalog commits (KCL-91)`.

### Task 7: A table that becomes managed is checked at once; a discovery scan only keeps its workflow

**Files:**
- Modify: `TM/application/domain/model/table/table_change.py` (`MANAGED = "managed"`); `TM/application/domain/model/table_reconciliation/wake_reason.py` (`TABLE_MANAGED = "table_managed"` replaces `DISCOVERY_SCAN`); `TM/application/service/table/register_discovered_table.py` (drops its `change` parameter and always sends `managed` for a managed registration); `TM/application/service/table/apply_discovery_to_known_table.py` (a `MANAGED` management change sends `managed`; otherwise as today); `TM/application/service/table/process_table_hint.py` and `sync_discovered_tables.py` (callers); `TEMPORAL/contracts/table_reconciliation/signal.py` (`TABLE_MANAGED = "table_managed"`); `TEMPORAL/outbound/table/send_table_change_temporal_gateway.py` (`"managed": TABLE_MANAGED`); `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py`; console `components/tabs/reconciliationText.ts` (`["table_managed", "Table managed"]` in place of `discovery_scan`)
- Test: `test_discovery_sync_services.py`, `test_table_timestamps.py` if it asserts sent changes; `test_send_table_change_temporal_gateway.py`; `test_wire_names.py`; `test_table_reconciliation_workflow.py` (the harness's default `start_signal` becomes `TABLE_MANAGED`; every `{"discovery_scan": 1}` expectation becomes `{"table_managed": 1}`), `test_raise_during_the_run_report.py`; the reconciliation record mapper test; `reconciliationText.test.ts`, `ReconciliationsTab.test.tsx`

**Interfaces:**
- Produces: signal `table_managed` → `self._wake("table_managed", cancels_stop=True)`; `table_seen` → `self._wake(None, cancels_stop=True)` (cancels a stop, plans nothing, counts nothing). `SendTableChangeGatewayInput.change == "managed"` is sent with `is_managed=True`, so the gateway signal-with-starts the workflow. If KCL-71 has landed, apply the same change to its versions of the two discovery helpers.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_scan_that_registers_a_managed_table_sends_managed(): ...     # gateway log: change "managed"
def test_a_hint_that_registers_a_managed_table_sends_managed(): ...      # not "updated"
def test_a_table_managed_again_sends_managed(): ...                      # unmanaged → rules manage → "managed"
def test_a_scan_of_a_managed_table_sends_seen(): ...                     # unchanged, catalog-wide scan → "seen"
def test_a_commit_hint_for_a_managed_table_sends_updated(): ...
def test_managed_signal_with_starts_the_workflow(): ...                  # gateway: start_workflow with start_signal "table_managed"
def test_a_table_that_became_managed_is_checked_at_once(): ...           # workflow record wake_reasons == {"table_managed": 1}
def test_a_discovery_scan_checks_nothing(): ...                         # running workflow, TABLE_SEEN → no record, wake_reasons {}
def test_a_discovery_scan_starts_a_missing_workflow_without_a_check(): ... # start_signal TABLE_SEEN → first record only at the schedule
def test_a_discovery_scan_after_stop_cancels_the_stop(): ...             # kept, now without a record
def test_wire_name_of_table_managed(): ...                              # TableReconciliationSignal.TABLE_MANAGED == "table_managed"
```

Console: `wakeText` of `{table_managed: 1}` reads "Table managed"; no "Discovery scan" label remains.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "managed or seen or discovery_scan or wire_names" -v`, then `<vitest> reconciliationText ReconciliationsTab`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`, then `<vitest>`
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): check a table when it becomes managed, not on every discovery scan (KCL-91)`.

### Task 8: e2e script and documentation

**Files:**
- Modify: `platform/25-lakehouse-control-plane/e2e.sh` (`ensure_policy` overrides), `platform/25-lakehouse-control-plane/README.md` (the policy body paragraph, the e2e steps 5 and 6, the platform settings paragraph, the manual-run row), `src/data-platform/backend/CLAUDE.md` (one paragraph after the per-table workflow paragraph: what a policy holds, an absent block, targets and `per`, options, cooldowns in platform settings, when a table is checked: schedule, the commit window, always-checks, `table_seen` only keeps the workflow), `src/data-platform/frontend/CLAUDE.md` (the policy editor's "In this policy" switch, options empty = procedure default, cooldowns on Platform settings), `docs/agents/known-follow-ups.md`, `docs/agents/project-history.md`

**Interfaces:**
- Consumes: the API shape of Task 3.

- [ ] **Step 1: Rewrite the e2e policies.** `tm-e2e-orders` (manual runs only): `.dry_run = true | .rewrite_data_files.options.min_input_files = 1 | .expire_snapshots.target = {min_snapshots_to_keep: 1, max_snapshot_age_seconds: ${EXPIRE_AGE_SECONDS}} | .remove_orphan_files.target.older_than_seconds = 86400` (dry run keeps it inert for scheduling while its blocks carry the values the manual run uses). `tm-e2e-regions`: `.on = {schedule: {every_seconds: 300}, catalog_commit: {debounce_seconds: 60}} | .rewrite_data_files.target.reducible_files.at_most = 1 | del(.rewrite_manifests, .expire_snapshots, .remove_orphan_files)` (the old `at_least: 2` is `at_most: 1`). Remove every jq path into `.operations`, `trigger_policy`, `execution_policy`, `cooldown_seconds` and `reconcile_interval_seconds`; any assertion that reads them follows the new shape. Run `uv run --directory /Users/kcl/Projects/retail-lakehouse pre-commit run shellcheck --all-files`.
- [ ] **Step 2: Docs.** README: replace the policy paragraph with the new body (point at `GET /v1/maintenance-policies/default`), list the four cooldown settings in the platform settings paragraph. `known-follow-ups.md`: remove "Every CDC commit sends a hint that triggers a full metadata scan in the plan; debounce planning." Add: a run's own commit (compaction, expiry) opens a commit window too and costs one extra check; a managed table whose workflow was lost is checked only at its schedule after a discovery scan restarts it; `per: partition` decides only whether compaction is due, the run compacts the whole table until KCL-94; `options` cover a curated subset of each procedure's arguments, another one is a new field; `small_manifests.at_most: 0` makes manifest rewrites due at every cooldown, since the newest manifest is usually small. `project-history.md`: one 2026-11-20 KCL-91 line (target-state content and its exact JSON keys, cooldowns as platform settings with their env names, the commit window, `table_managed`, `discovery_scan` gone, the runtime's procedure options).
- [ ] **Step 3: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `docs(table-maintenance): describe target-state maintenance policies and the e2e policies (KCL-91)`.

### Task 9: Verify on a rebuilt cluster (controller)

- [ ] **Step 1:** `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse onboard KUBE_CONTEXT=retail-lakehouse`; `task -d /Users/kcl/Projects/retail-lakehouse apps:validate KUBE_CONTEXT=retail-lakehouse` exits 0.
- [ ] **Step 2:** `GET /v1/maintenance-policies/default` equals the Global Constraints JSON plus the server fields; `GET /v1/platform-settings` lists the four cooldown items with 3600, 21600, 21600, 604800. A POST with `expire_snapshots.options.retain_last` answers 422.
- [ ] **Step 3:** Create `iceberg.kcl91.a` (the `trino_sql` way `e2e.sh` does) and a discovery rule (or, after KCL-71, a discovery policy) that manages `iceberg / kcl91 / *`. The table's first reconciliation records `{"table_managed": 1}`, and later discovery scans add no reconciliation records.
- [ ] **Step 4:** Create policy `kcl91` with `on: {schedule: {every_seconds: 300}, catalog_commit: {debounce_seconds: 120}}` and only `rewrite_data_files` (`at_most: 1`, `per: table`), attach it to `iceberg.kcl91` (record shows `policy_changed`). Run 10 single-row `INSERT`s within one minute: exactly one reconciliation lands about 120 s after the first commit, with `catalog_commit` counting the commits it saw, and starts a whole-table `rewrite_data_files` run. The next one without writes lands about 300 s after the last check, reason `schedule`.
- [ ] **Step 5:** Update `kcl91` to `every_seconds: 600` without `catalog_commit`: a `policy_changed` check lands at once; further inserts produce no reconciliation until about 600 s later (reason `schedule`).
- [ ] **Step 6:** Update `kcl91` to drop `rewrite_data_files` and add `expire_snapshots` (`min_snapshots_to_keep: 1`, `max_snapshot_age_seconds: 60`): the next reconciliation shows `rewrite_data_files` as `off` and no new rewrite run; expiry runs once a snapshot is over the age.
- [ ] **Step 7:** In the console: create a policy with the editor (keyboard only: Tab, Space on the switches, Enter to save), see it in the list with its Checks text, open its version page (operations not in it read "Not in this policy"), and see the cooldowns on the Platform settings page.
- [ ] **Step 8:** `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` passes. Then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`; record the results on KCL-91 in a dated comment and push only when the user asks.
