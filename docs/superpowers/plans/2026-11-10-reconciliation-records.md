# Reconciliation Records and Dry Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store every table reconciliation as a record, show the records on a new Reconciliations tab, and add a per-table dry run and a "Reconcile now" action.

**Architecture:**

- **New aggregate.** `TableReconciliation` lives in `context/table_maintenance` with its own SQL table.
- **What the plan activity returns.** Besides the operations to run, it now returns:
  - per-operation checks, built from new `Measurement` value objects that `assess_maintenance` produces;
  - the dry-run flag.
- **Who writes the record.** `TableReconciliationWorkflow` tracks why it woke. Once a start has been attempted, it calls a new `record_table_reconciliation` activity. The record therefore never names a run that does not exist.
- **Console.** It reads the records through `GET /v1/tables/{uuid}/reconciliations` and shows them as the approved timeline-and-drawer design.

**Tech Stack:**

- Python 3.13, FastAPI, SQLAlchemy Core, Temporal Python SDK, pytest;
- React 19, TanStack Query and Orval, MSW, Vitest and Storybook 10;
- the `@retail-lakehouse/design-system` package.

**Spec:** `docs/superpowers/specs/2026-11-10-reconciliation-records-design.md`

## Global Constraints

**Commands and process**

- TDD always: write the failing test, run it and watch it fail, then implement, then run it and watch it pass.
- Every commit passes, from the repo root:
  - `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest -q`
  - `uv run --project src/data-platform/backend --directory src/data-platform/backend ty check`
  - `uv run --project src/data-platform/backend --directory src/data-platform/backend ruff check .`
  - `uv run --project src/data-platform/backend --directory src/data-platform/backend lint-imports`
  - For frontend tasks, also `npm --prefix src/data-platform/frontend run lint`, `npm --prefix src/data-platform/frontend run typecheck` and `npm --prefix src/data-platform/frontend test -- --run`.
- Never `cd`; use absolute paths or `--prefix` / `--directory`. Use `uv run`, never bare `python` or `pytest`.
- Don't run prettier over the frontend or the design system. Add no new dependencies.
- Commits: conventional, lowercase subject, lines ≤ 100 characters. Every message ends with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. Commit on `main` and stage explicit paths. Do not push.
- Cluster commands always pass `KUBE_CONTEXT=retail-lakehouse`. kubectl puts the verb first and flags last (`kubectl get pods -n x --context retail-lakehouse`).

**Backend structure** (rules in `src/data-platform/backend/CLAUDE.md`; enforced by `tests/architecture`)

- The aggregate axis must hold, so every layer gets a `table_reconciliation` directory.
- Imports go only through boundaries (`__init__.py` re-exports).
- No infrastructure words in `application/` names.
- Inbound port files are named `{verb}_{noun}/{input,output,use_case}.py`, and services must start with a known verb.
- Web DTOs end in `ApiRequest` / `ApiResponse`.
- Code style: one object per file, `from __future__ import annotations` in every module, `StrEnum` for string enums, `abc.ABC` for interfaces.

**Spec values, verbatim**

- Wake reasons: `schedule`, `catalog_commit`, `settings_changed`, `resumed`, `paused`, `manual_run`, `reconcile_now`, `previous_run_finished`.
- Operation results: `started`, `would_start`, `start_failed`, `not_needed`, `cooling_down`, `off`, `not_checked`.
- Outcome: `planned` or `skipped`. The skip reasons are `paused`, `dropped`, `excluded` and `not_found`.
- Measurement fields: `key`, `observed`, `unit` (`count` | `bytes` | `seconds`), `threshold`, `comparison` (`>=` | `>` | `<` | `<=`), `met`.
  - A context measurement has `threshold`, `comparison` and `met` all null.
  - `combine` is `all` or `any`.
- Retention: 30 days.
- List page size: default 50.
- Console copy, verbatim:
  - Tab: "Reconciliations"
  - Header action: "Reconcile now"
  - Empty list: "No reconciliations yet."
  - Collapsed measurements: "All measurements"
  - Missing run: "This run is no longer available"
  - Folded quiet stretch: "{n} reconciliations found nothing to do, {first}–{last}"
- Status colours: notice for `started` and `would_start`, neutral for every other result.

## Review Focus

These are the cases most likely to break that no task's main test path covers. Each one is pinned by a test in the task named.

1. **Wakes arriving while a run is in flight must not be lost.** Their reasons appear in the record of the reconciliation that runs after `maintenance_finished`. Task 7.
2. **A table in dry run whose user clicks "Run maintenance" still runs.** The record shows `started` with `dry_run` true. Task 4 and Task 7.
3. **A failed child start records `start_failed`, never `started` with a run id.** Task 7.
4. **Seven or more quiet hourly reconciliations fold into one line, and a reconciliation that started something breaks the fold.** Task 9.
5. **Opening the Maintenance tab with `?run=` for an unknown id shows the missing-run banner and the normal list, without crashing.** Task 10.

---

### Task 1: Measurements in assessments

**Files:**

- Create `context/table_maintenance/application/domain/model/shared/measurement.py`. All paths in this plan are under `src/data-platform/backend/` unless they start with `src/`.
- Create `context/table_maintenance/application/domain/model/shared/measurement_unit.py`.
- Create `context/table_maintenance/application/domain/model/shared/measurement_comparison.py`.
- Create `context/table_maintenance/application/domain/model/shared/condition_combine.py`.
- Modify `context/table_maintenance/application/domain/model/shared/operation_assessment.py` and the package `__init__.py`.
- Modify `context/table_maintenance/application/domain/service/table/assess_maintenance.py`.
- Test `tests/context/table_maintenance/application/domain/service/table/test_assess_maintenance.py` (extend it).

**Interfaces:**

- **Produces:**
  - `MeasurementUnit(StrEnum)`: `COUNT="count"`, `BYTES="bytes"`, `SECONDS="seconds"`.
  - `MeasurementComparison(StrEnum)`: `AT_LEAST=">="`, `MORE_THAN=">"`, `LESS_THAN="<"`, `AT_MOST="<="`.
  - `ConditionCombine(StrEnum)`: `ALL="all"`, `ANY="any"`.
  - `Measurement(ValueObject)`, a frozen dataclass:
    - fields `key: str`, `observed: int`, `unit: MeasurementUnit`, `threshold: int | None = None`, `comparison: MeasurementComparison | None = None`;
    - a property `met -> bool | None`, which is None when threshold is None;
    - `__post_init__` rejects a threshold without a comparison, and a comparison without a threshold.
  - `OperationAssessment` gains `combine: ConditionCombine = ConditionCombine.ALL` and `measurements: tuple[Measurement, ...] = ()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_compaction_reports_reducible_files_and_context(): ...
    # partition scope, 2 partitions with 7 and 1 reducible files, min_reducible_files=5
    # assessment.measurements == (
    #   Measurement("reducible_files", 7, MeasurementUnit.COUNT, 5, MeasurementComparison.AT_LEAST),
    #   Measurement("target_file_size", <resolved target>, MeasurementUnit.BYTES),
    #   Measurement("qualifying_partitions", 1, MeasurementUnit.COUNT),
    # ); assessment.combine is ConditionCombine.ALL
def test_compaction_table_scope_has_no_qualifying_partitions_measurement(): ...
def test_manifests_report_small_manifests(): ...       # key "small_manifests", threshold min_small_manifests, AT_LEAST
def test_snapshots_report_expirable_snapshots(): ...   # key "expirable_snapshots", threshold 1, AT_LEAST
def test_orphans_have_no_measurements(): ...
def test_disabled_operation_has_no_measurements(): ...
def test_cooldown_keeps_the_measurements(): ...
def test_measurement_met_and_context():                # in tests/.../domain/model/shared/test_measurement.py
    assert Measurement("x", 5, MeasurementUnit.COUNT, 5, MeasurementComparison.AT_LEAST).met is True
    assert Measurement("x", 5, MeasurementUnit.COUNT, 5, MeasurementComparison.MORE_THAN).met is False
    assert Measurement("x", 5, MeasurementUnit.BYTES).met is None
    with pytest.raises(ValueError): Measurement("x", 5, MeasurementUnit.COUNT, 5)
```

- [ ] **Step 2: Run them and watch them fail.** Run `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/domain -q`. Expected: an ImportError for `Measurement`.
- [ ] **Step 3: Add the value objects and fill `measurements` in `_assess_compaction`, `_assess_manifests` and `_assess_snapshots`.** The existing `measured` and `threshold` fields stay as they are; other code reads them.
- [ ] **Step 4: Run the whole backend suite.** Expected: PASS.
- [ ] **Step 5: Commit.** `feat(table-maintenance): measure each assessed operation`

### Task 2: Dry run setting

**Files:**

- Modify `context/table_maintenance/application/domain/model/shared/maintenance_settings.py`, adding `dry_run: bool = False`.
- Modify `context/table_maintenance/application/service/shared/maintenance_settings_from_dict.py`, adding `dry_run` to `_ROOT_KEYS`. It must be a bool via `_bool`, and a missing key means False.
- Modify `context/table_maintenance/application/service/shared/maintenance_settings_to_dict.py`.
- Modify the web settings DTOs that carry `reconcile_interval_seconds`. Find them with `grep -rn reconcile_interval_seconds context/table_maintenance/adapter/inbound/web`; they cover table settings and presets.
- Regenerate `src/data-platform/backend/openapi.json` and `src/data-platform/frontend/src/api/generated` with `task dev:generate-api`.
- Tests:
  - `tests/context/table_maintenance/application/service/shared/test_maintenance_settings_conversion.py`
  - `tests/context/table_maintenance/adapter/outbound/shared/sql/test_maintenance_settings_codec.py`
  - the table-settings route test

**Interfaces:**

- **Produces:**
  - `MaintenanceSettings.dry_run: bool`;
  - the settings dict key `"dry_run"`;
  - the API field `dry_run: bool` on every settings request and response.

- [ ] **Step 1: Write the failing tests:**
  - `test_dry_run_round_trips` (`to_dict`, then `from_dict`, keeps True);
  - `test_missing_dry_run_means_false` (a stored dict without the key);
  - `test_dry_run_must_be_boolean` (`"yes"` raises `ValidationError`);
  - a route test: PUT settings with `"dry_run": true`, then GET returns it.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement.** Run `task dev:generate-api`.
- [ ] **Step 4: Run the backend suite, then `task checks:contract-test-console-api`.** Expected: PASS and a clean diff after commit.
- [ ] **Step 5: Commit.** `feat(table-maintenance): add a dry-run setting`

### Task 3: TableReconciliation aggregate and repository

**Files:**

- Create `context/table_maintenance/application/domain/model/table_reconciliation/`. It holds `__init__.py` and one file per object:
  - `table_reconciliation.py` (the `TableReconciliation(AggregateRoot[TableReconciliationId])`);
  - `table_reconciliation_id.py`;
  - `wake_reason.py` (the `WakeReason` StrEnum, values from Global Constraints);
  - `reconciliation_outcome.py` (the `ReconciliationOutcome` StrEnum: `PLANNED="planned"`, `SKIPPED="skipped"`);
  - `operation_result.py` (the `OperationResult` StrEnum, values from Global Constraints);
  - `operation_outcome.py`;
  - `invalid_reconciliation.py`.
- Create `context/table_maintenance/application/port/outbound/table_reconciliation/__init__.py` and `table_reconciliations_repo.py`.
- Create `context/table_maintenance/adapter/outbound/table_reconciliation/__init__.py`.
- Create `context/table_maintenance/adapter/outbound/table_reconciliation/sql/`, holding `__init__.py`, `table_reconciliations_table.py`, `table_reconciliation_row_mapper.py` and `table_reconciliations_sql_repo.py`.
- Modify `context/table_maintenance/adapter/outbound/shared/sql/create_schema.py`, adding the package to `AGGREGATE_SQL_PACKAGES`.
- Create `tests/context/table_maintenance/fakes/in_memory_table_reconciliations_repo.py`.
- Test:
  - `tests/context/table_maintenance/application/domain/model/table_reconciliation/test_table_reconciliation.py`
  - `tests/context/table_maintenance/adapter/outbound/table_reconciliation/test_table_reconciliations_sql_repo.py`
  - `tests/context/table_maintenance/adapter/outbound/shared/sql/test_create_schema.py` (extend it)

**Interfaces:**

- **Produces:**
  - `OperationOutcome(ValueObject)`, with the fields:
    - `operation: MaintenanceOperation`;
    - `result: OperationResult`;
    - `combine: ConditionCombine`;
    - `measurements: tuple[Measurement, ...]`;
    - `next_eligible_at: datetime | None = None`.
  - `TableReconciliation`, a dataclass with `eq=False`:
    - fields `id`, `table_uuid: TableId`, `reconciled_at: datetime`, `wake_reasons: dict[WakeReason, int]`, `dry_run: bool`, `outcome: ReconciliationOutcome`, `skip_reason: str | None`, `operations: tuple[OperationOutcome, ...]`, `run_id: TableMaintenanceRunId | None`;
    - the classmethod `record(...)` with the same arguments, which validates the fields below.
  - What `record(...)` rejects with `InvalidReconciliation`:
    - an empty `wake_reasons`, or a count below 1;
    - `skipped` without a skip reason, `planned` with one, or `skipped` with operations;
    - a `run_id` set while no operation is `started`, or an operation `started` while `run_id` is None.

    It also orders operations by `MaintenanceOperation.ordered()`.
  - `TableReconciliationsRepo(Repository[TableReconciliation])`, which adds:
    - `list_by_table(self, table_uuid: TableId, *, before: datetime | None = None, limit: int = 50) -> list[TableReconciliation]`, newest first, strictly before `before`;
    - `delete_older_than(self, table_uuid: TableId, cutoff: datetime) -> int`.
  - SQL table `table_reconciliations`, with columns:
    - `id` (primary key), `table_uuid`, `reconciled_at` (UtcDateTime), `wake_reasons_json`, `dry_run`, `outcome`, `skip_reason`, `operations_json`, `run_id`;
    - index `ix_table_reconciliations_table_reconciled` on (`table_uuid`, `reconciled_at`).

- [ ] **Step 1: Write the failing domain tests**, one per rejection rule above, plus:
  - `test_record_orders_operations_canonically`;
  - `test_started_operation_carries_the_run`.
- [ ] **Step 2: Write the failing repo tests.** They use the SQLite engine fixture the runs repo test uses.
  - `test_create_and_get_round_trip`, including measurements with null thresholds and `next_eligible_at`;
  - `test_list_by_table_newest_first_with_cursor`;
  - `test_list_by_table_respects_limit`;
  - `test_delete_older_than_only_touches_that_table`.

  Run both test files the same way and the fake against the same tests. Follow how the runs repo shares tests with `in_memory_table_maintenance_runs_repo.py`.
- [ ] **Step 3: Run them and watch them fail.**
- [ ] **Step 4: Implement the domain model, the port, the SQL adapter and the fake.** Update `AGGREGATE_SQL_PACKAGES`.
- [ ] **Step 5: Run the whole suite, including `tests/architecture`.** Expected: PASS. The aggregate axis and the one-repository-per-aggregate tests pick up `table_reconciliation`.
- [ ] **Step 6: Commit.** `feat(table-maintenance): add the table reconciliation aggregate`

### Task 4: The plan reports checks and honours dry run

**Files:**

- Modify `context/table_maintenance/application/port/inbound/table/plan_table_maintenance/output.py`, adding a `PlanTableMaintenanceUseCaseOutputCheckItem` and a `PlanTableMaintenanceUseCaseOutputMeasurementItem`.
- Modify `context/table_maintenance/application/service/table/plan_table_maintenance.py`.
- Modify `context/table_maintenance/application/domain/service/table/` (`plan_scheduled_maintenance`) only if it needs to hand out the assessment.
- Test `tests/context/table_maintenance/application/service/table/test_plan_table_maintenance_service.py`.

**Interfaces:**

- **Consumes:** Task 1 `Measurement` and `OperationAssessment.measurements`; Task 2 `MaintenanceSettings.dry_run`.
- **Produces:**
  - `PlanTableMaintenanceUseCaseOutput` gains three fields:
    - `dry_run: bool` (False for a skip);
    - `table_found: bool` (False only when the maintenance row is missing);
    - `checks: list[PlanTableMaintenanceUseCaseOutputCheckItem]`.
  - Each check item has `operation: str`, `verdict: str`, `combine: str`, `measurements: list[PlanTableMaintenanceUseCaseOutputMeasurementItem]` and `next_eligible_at: datetime | None`.
    - `verdict` is one of `due`, `not_needed`, `cooling_down`, `off` and `not_checked`.
  - Measurement items have `key`, `observed`, `unit`, `threshold`, `comparison` and `met`, as primitives.
  - For a scheduled plan, the checks come from `assess_maintenance`:
    - DUE → `due`, NOT_DUE → `not_needed`, COOLDOWN → `cooling_down`, DISABLED → `off`.
    - If `dry_run` is set, `operations` is `[]` while `checks` still says `due`.
  - For a manual plan, the requested operations are `due` with no measurements and the rest are `not_checked`. `operations` is returned even in dry run.
  - For a skip, `checks` is `[]`.

- [ ] **Step 1: Write the failing tests:**
  - `test_scheduled_plan_reports_a_check_per_operation`;
  - `test_dry_run_plans_no_operations_but_reports_due`;
  - `test_manual_plan_runs_in_dry_run`;
  - `test_manual_plan_marks_unrequested_not_checked`;
  - `test_missing_table_is_not_found_in_maintenance` (`table_found` False, status `skip`, reason `dropped`);
  - `test_paused_table_skips_with_table_found`.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement.** Keep the existing fields and the `status` / `reason` meanings unchanged.
- [ ] **Step 4: Run the backend suite.** Expected: PASS.
- [ ] **Step 5: Commit.** `feat(table-maintenance): report per-operation checks from the plan`

### Task 5: Record a reconciliation

**Files:**

- Create `context/table_maintenance/application/port/inbound/table_reconciliation/record_table_reconciliation/`, holding `__init__.py`, `input.py`, `output.py` and `use_case.py`, plus the package `__init__.py`.
- Create `context/table_maintenance/application/service/table_reconciliation/__init__.py` and `record_table_reconciliation.py`.
- Test `tests/context/table_maintenance/application/service/table_reconciliation/test_record_table_reconciliation_service.py`.

**Interfaces:**

- **Consumes:** Task 3's aggregate and repo, and the primitive check items from Task 4.
- **Produces:**
  - `RecordTableReconciliationUseCaseInput`, with fields:
    - `reconciliation_id: str`, `table_uuid: str`, `reconciled_at: datetime`;
    - `wake_reasons: dict[str, int]`, `dry_run: bool`;
    - `status: str` (`planned` | `skip`), `skip_reason: str | None`;
    - `checks: list[dict]`, the Task 4 check items as dicts;
    - `run_id: str | None`, `run_start_failed: bool`.
  - `RecordTableReconciliationUseCaseOutput(recorded: bool)`.
  - `RecordTableReconciliationService(RecordTableReconciliationUseCase)`, whose constructor is `__init__(self, reconciliations_repo: TableReconciliationsRepo)`. Its rules:
    - verdict `due` becomes:
      - `started` if `run_id`;
      - `start_failed` if `run_start_failed`;
      - `would_start` if `dry_run`;
      - otherwise a `ValidationError` (a due check with no run and no reason is a bug);
    - the other verdicts map by the same name;
    - status `skip` stores outcome `skipped` with the skip reason;
    - it stores the record, then deletes this table's records older than `reconciled_at − 30 days`;
    - recording an id that already exists is a no-op, because Temporal may retry the activity.

- [ ] **Step 1: Write the failing tests:**
  - `test_started_due_operations_link_the_run`;
  - `test_dry_run_due_becomes_would_start`;
  - `test_failed_start_records_start_failed_without_run`;
  - `test_skip_is_recorded_with_reason`;
  - `test_records_older_than_thirty_days_are_purged`, with records at −31 d and −29 d, of which only the first is gone;
  - `test_recording_twice_keeps_one_record`;
  - `test_unknown_wake_reason_is_rejected` (ValidationError).
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement.** Add `"Record"` to `KNOWN_VERBS` in `tests/architecture/test_service_structure.py` only if it is not there yet.
- [ ] **Step 4: Run the backend suite.** Expected: PASS.
- [ ] **Step 5: Commit.** `feat(table-maintenance): record table reconciliations`

### Task 6: List reconciliations over the API

**Files:**

- Create `context/table_maintenance/application/port/inbound/table_reconciliation/list_table_reconciliations/`, holding `input.py`, `output.py`, `use_case.py` and `__init__.py`.
- Create `context/table_maintenance/application/service/table_reconciliation/list_table_reconciliations.py`.
- Create `context/table_maintenance/adapter/inbound/web/table_reconciliation/`, holding `__init__.py`, `router.py` and `dto.py`. Register the router where the runs router is registered (`adapter/inbound/web/register_routes.py`).
- Modify the `bootstrap/container` wiring, following how `ListTableMaintenanceRunsService` is wired.
- Regenerate the OpenAPI document and the Orval client.
- Test `tests/context/table_maintenance/adapter/inbound/web/table_reconciliation/test_table_reconciliation_routes.py` and the service test.

**Interfaces:**

- **Produces:**
  - Route `GET /v1/tables/{table_uuid}/reconciliations?before=<iso datetime>&limit=<1..200, default 50>`, returning `list[TableReconciliationApiResponse]`, newest first.
  - `TableReconciliationApiResponse` has the fields:
    - `reconciliation_id`, `table_uuid`, `reconciled_at`;
    - `wake_reasons: dict[str, int]`, `dry_run`, `outcome`, `skip_reason`;
    - `operations: list[ReconciliationOperationApiResponse]`;
    - `run_id`.
  - `ReconciliationOperationApiResponse` has `operation`, `result`, `combine`, `measurements: list[ReconciliationMeasurementApiResponse]` and `next_eligible_at`.
  - `ReconciliationMeasurementApiResponse` has `key`, `observed`, `unit`, `threshold`, `comparison` and `met`.

- [ ] **Step 1: Write the failing tests:**
  - `test_lists_newest_first`;
  - `test_before_pages_older_records`;
  - `test_limit_above_200_is_422`;
  - `test_unknown_table_returns_empty_list` (the runs route behaves the same way);
  - `test_context_measurement_has_null_threshold_and_met`.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement, wire it, and run `task dev:generate-api`.**
- [ ] **Step 4: Run the backend suite and `task checks:contract-test-console-api`.**
- [ ] **Step 5: Commit.** `feat(table-maintenance): list a table's reconciliations`

### Task 7: The workflow records why it woke, and reconcile now

**Files:**

- Modify `context/table_maintenance/application/domain/model/table/table_change.py`, adding `RECONCILE_REQUESTED = "reconcile_requested"`.
- Create the `context/table_maintenance/application/port/inbound/table/trigger_table_reconciliation/` port and `context/table_maintenance/application/service/table/trigger_table_reconciliation.py`.
  - Shape them after `trigger_table_maintenance`, without operations: the table must exist (else `NotFoundError`) and be enrolled (else `ConflictError`).
- Modify `context/table_maintenance/adapter/inbound/web/table/router.py`, adding `POST /{table_uuid}/reconcile` → 202 `{"accepted": true}`.
- Modify `context/table_maintenance/adapter/hybrid/temporal/contracts/table_reconciliation/signal.py`, adding `RECONCILE_NOW = "reconcile_now"`.
- Modify `contracts/table_reconciliation/activity.py`, adding `RECORD_TABLE_RECONCILIATION = "record_table_reconciliation"`.
- Modify `contracts/table_reconciliation/workflow_input.py`, adding `wake_reasons: dict[str, int] | None = None` and documenting it.
- Modify `context/table_maintenance/adapter/hybrid/temporal/outbound/table/send_table_change_temporal_gateway.py`, mapping `"reconcile_requested"` to `RECONCILE_NOW`.
- Modify `context/table_maintenance/adapter/hybrid/temporal/inbound/activities/table_reconciliation_activities.py`:
  - add the `record_table_reconciliation` activity;
  - `plan_table_maintenance` passes `table_found`, `dry_run` and `checks` through.
- Modify `context/table_maintenance/adapter/hybrid/temporal/inbound/workflows/table_reconciliation_workflow.py`.
- Modify the `bootstrap/container` wiring and the worker's activity registration.
- Tests:
  - `tests/context/table_maintenance/adapter/hybrid/temporal/inbound/test_table_reconciliation_workflow.py`
  - `tests/context/table_maintenance/adapter/hybrid/temporal/contracts/test_wire_names.py`
  - the gateway, route and service tests

**Interfaces:**

- **Consumes:** Task 4 plan output; Task 5 `RecordTableReconciliationUseCase`.
- **Workflow behaviour:**
  - Replace `_woken: bool` with `_wake_reasons: dict[str, int]`.
    - Each signal handler adds its reason (+1).
    - A `_wait` that ends on the timer adds `schedule`.
    - `stop` adds nothing.
  - Reasons are cleared only right after a plan activity returns, never when the loop wakes for an in-flight run. They are carried through continue-as-new as `wake_reasons`.
  - `_woken` checks become `bool(self._wake_reasons)`.
  - Before planning, generate `reconciliation_id = str(workflow.uuid4())`. Generate the run id there as well, and keep it for `_start_run`.
  - After the plan, call `RECORD_TABLE_RECONCILIATION` with the reconciliation id, the table uuid, `now`, the reasons, the plan's `dry_run`, `status`, `reason` and `checks`, and two start fields:
    - `run_id`: set only when `_start_run` succeeded;
    - `run_start_failed`: true when it raised.
  - Skip that call when the plan says `table_found` is False.
  - A failed record activity is logged and does not stop the loop. Use the same timeout and retry as the plan activity.
  - A plan activity that fails records nothing. Its reasons are cleared as today's code clears the manual trigger.
  - The query `state()` gains `wake_reasons`.

- [ ] **Step 1: Write the failing workflow tests**, with the existing time-skipping harness and fake activities:
  - `test_timer_wake_records_schedule`;
  - `test_three_catalog_commits_during_a_run_are_recorded_after_it_finishes` (reasons `{catalog_commit: 3, previous_run_finished: 1}`);
  - `test_reconcile_now_records_reconcile_now`;
  - `test_dry_run_plan_starts_nothing_and_records`;
  - `test_failed_child_start_records_start_failed` (the fake start raises);
  - `test_missing_table_records_nothing`;
  - `test_wake_reasons_survive_continue_as_new`;
  - `test_failed_record_does_not_stop_the_loop`.
- [ ] **Step 2: Write the failing wire-name, gateway, service and route tests:**
  - `reconcile_now` and `record_table_reconciliation` pinned;
  - `reconcile_requested` sends `reconcile_now`;
  - 404 for an unknown table, 409 for a paused one, 202 otherwise.
- [ ] **Step 3: Run them and watch them fail.**
- [ ] **Step 4: Implement and wire, then run `task dev:generate-api`.**
- [ ] **Step 5: Run the whole backend suite, including `tests/architecture/test_temporal_workflow_*`, and `task checks:contract-test-console-api`.**
- [ ] **Step 6: Commit.** `feat(table-maintenance): record why each reconciliation woke`

### Task 8: Design system, DataTable opens rows by id

**Files:**

- Modify `src/design-system/src/components/DataTable/DataTable.tsx` and `DataTable.stories.tsx`.

**Interfaces:**

- **Produces:** the prop `initialExpandedRowIds?: string[]`. Those rows start expanded, matched by `getRowId`. Unknown ids are ignored.

- [ ] **Step 1: Write the story `InitialExpanded` first**, with a play function asserting that row "b" starts expanded and its detail is visible, and that an unknown id is ignored. Run `npm --prefix src/design-system run test:stories -- DataTable` and watch it fail.
- [ ] **Step 2: Implement it through TanStack's `initialState.expanded`.**
- [ ] **Step 3: Run the design-system unit tests and story tests.** Expected: PASS.
- [ ] **Step 4: Commit.** `feat(design-system): let a data table open rows by id`

### Task 9: Console, Reconciliations tab

**Files:**

- Create `src/data-platform/frontend/src/components/tabs/ReconciliationsTab.tsx` (the list, folding and drawer), `ReconciliationsTab.test.tsx` and `reconciliationText.ts` (headline, wake text and reason sentences).
- Modify `src/data-platform/frontend/src/pages/TablePage.tsx`:
  - add `{ key: "reconciliations", label: "Reconciliations" }` after Maintenance, wrapped in `MaintenanceGate`;
  - update the "six tabs" comment.
- Modify `src/data-platform/frontend/src/stories/storyData.ts`. Add `RECONCILIATIONS`, modelled on the mockup:
  - one started record with catalog commit × 3;
  - four quiet scheduled records;
  - one dry-run record;
  - one skipped (paused) record.
- Modify `src/data-platform/frontend/src/stories/lakehouseHandlers.ts`, answering the list from `RECONCILIATIONS` and honouring `before` and `limit`.
- Modify `src/data-platform/frontend/src/pages/TablePage.stories.tsx`. Add the stories:
  - `Reconciliations`;
  - `ReconciliationDrawer` (play: open the first item, then check the headline, the run link and "All measurements");
  - `ReconciliationsEmpty`;
  - `ReconciliationsError`;
  - `ReconciliationsPhone`.
- Delete `src/data-platform/frontend/src/stories/mockups/ReconcileHistoryMockup.stories.tsx` and its now-empty directory.

**Interfaces:**

- **Consumes:** the Orval hook for `GET /v1/tables/{uuid}/reconciliations` (Task 6) and the design-system `Drawer`.
- **Produces:** `ReconciliationsTab({ tableUuid }: { tableUuid: string })`, plus these exports from `reconciliationText.ts`:
  - `headline(r)`;
  - `wakeText(r)` (the most frequent reason first, ties in the Global Constraints order);
  - `reasonSentence(op)`.
- **Behaviour, as the spec says:**
  - Day groups headed as in the Commits tab (h2). Each record is one row.
  - Consecutive records that started nothing and share the same headline fold into one line, with the copy from Global Constraints.
  - A button opens the Drawer. Its operation blocks are ordered `started`, `would_start`, `start_failed`, `not_needed`, `cooling_down`, `off`, `not_checked`.
  - The run link goes to the Maintenance tab with `?run=<id>`.
  - `StatusBadge`: notice for `started` and `would_start`, neutral otherwise.
  - Load more: a "Show older" button fetches with `before` set to the oldest `reconciled_at`.

- [ ] **Step 1: Write the failing unit tests in `ReconciliationsTab.test.tsx`.** Use MSW with `stubCatalogApi` or the generated mock handler.
  - `groups records by day under h2 headings`;
  - `folds seven quiet records into one line` (text "7 reconciliations found nothing to do");
  - `a started record breaks the fold`;
  - `dry run record shows Would start and a Dry run badge`;
  - `drawer shows wake reasons with counts` ("Catalog commit × 3");
  - `drawer lists operations in result order`;
  - `reason sentence cites only deciding measurements`;
  - `All measurements lists context measurements without a met mark`;
  - `run link points at the maintenance tab with the run id`;
  - `shows No reconciliations yet. when empty`;
  - `Show older requests before the oldest record`.

  In `reconciliationText.test.ts`, test each result's sentence.
- [ ] **Step 2: Run `npm --prefix src/data-platform/frontend test -- --run ReconciliationsTab` and watch it fail.**
- [ ] **Step 3: Implement.** Build it from design-system parts only (`Drawer`, `StatusBadge`, `Badge`, `TextLink` with the router `Link` passed through `asChild`, icons). Use semantic utilities only. Identifiers go in `font-mono` and numbers in `tabular-nums`.
- [ ] **Step 4: Add the stories and run the story tests:** `npm --prefix src/data-platform/frontend run test:stories -- TablePage`. Expected: PASS, including axe and no horizontal scroll at phone width.
- [ ] **Step 5: Run the console lint, typecheck and unit tests.**
- [ ] **Step 6: Commit.** `feat(console): show a table's reconciliations`

### Task 10: Console, Reconcile now, dry run, and the run link target

**Files:**

- Modify `src/data-platform/frontend/src/components/TableHeader.tsx`:
  - add a "Reconcile now" action item beside "Run maintenance", only when maintenance manages the table. It posts through the generated mutation and invalidates the reconciliations list key in `onSettled`, and is disabled while pending;
  - show a `Badge` "Dry run" in the header meta when the table's settings have `dry_run`.
- Modify `src/data-platform/frontend/src/components/SettingsForm.tsx`: add a `Switch` for `dry_run` labelled "Dry run". Its description: "Reconcile and record as usual, but start no maintenance. Run maintenance still runs."
- Modify `src/data-platform/frontend/src/components/tabs/MaintenanceTab.tsx`:
  - read `?run=` and pass it as `initialExpandedRowIds`;
  - if the id is not in the loaded runs, show a `Banner` reading "This run is no longer available" above the list.
- Tests: `TableHeader.test.tsx`, `SettingsTab.test.tsx` and `MaintenanceTab.test.tsx`, plus a `TablePage` story `DryRunHeader`.

- [ ] **Step 1: Write the failing tests:**
  - `Reconcile now posts and refreshes reconciliations`;
  - `Reconcile now is hidden for an unmanaged table`;
  - `dry run badge shows when settings say dry run`;
  - `saving the dry run switch sends dry_run true`;
  - `maintenance tab opens the run named in the url`;
  - `unknown run id shows the missing-run banner and the list`.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the console lint, typecheck, unit tests and story tests.**
- [ ] **Step 5: Commit.** `feat(console): reconcile now, dry run, and open a run from a link`

### Task 11: End-to-end check and docs

**Files:**

- Modify `platform/25-lakehouse-control-plane/e2e.sh`. After the existing manual `POST /maintenance` run finishes, assert that `GET /v1/tables/${ORDERS_UUID}/reconciliations` holds a record where:
  - `wake_reasons.manual_run >= 1`;
  - one operation is `started`;
  - its `run_id` equals the run the test waited for.

  Then `POST /reconcile`, and wait (with the script's existing polling style) for a record with `wake_reasons.reconcile_now`.
- Modify `docs/agents/project-history.md` (one line), `src/data-platform/backend/CLAUDE.md` (add `table_reconciliation` to the table_maintenance aggregate list) and `src/data-platform/frontend/CLAUDE.md` (the table page lists the Reconciliations tab).
- Modify `CLAUDE.md` (Project Vision aggregates list: add `TableReconciliation`).

- [ ] **Step 1: Add the e2e assertions.** Shell-check them with `shellcheck platform/25-lakehouse-control-plane/e2e.sh`.
- [ ] **Step 2: Update the docs.**
- [ ] **Step 3: Run `task pre-pr`.** Expected: every check passes.
- [ ] **Step 4: Commit.** `test(table-maintenance): check reconciliation records end to end` and `docs: record reconciliation records`.

### Task 12: Verify on the running minikube

No code. Each step is a check with an expected result.

- [ ] **Step 1: Wait for idle runs.**
  - Confirm no maintenance run is in flight: every table's runs have `finished_at` set. Check the console Maintenance tabs, or `GET /v1/tables/{uuid}/table-maintenance-runs`.
  - Wait if one is running; the spec requires it.
- [ ] **Step 2: Build and deploy the backend and console images.** Use the `minikube-deploy` skill with `KUBE_CONTEXT=retail-lakehouse`. Expected: the new pods are Ready and the migrate job created `table_reconciliations`.
- [ ] **Step 3: Restart the reconciliation workflows.**
  - Terminate every running `table-reconciliation-*` workflow (`temporal workflow terminate --query 'WorkflowType="<TABLE_RECONCILIATION_WORKFLOW>" AND ExecutionStatus="Running"'` through the Temporal admin tools pod).
  - Trigger discovery sync, or wait for its schedule.
  - Expected: one running reconciliation workflow per enrolled table again.
- [ ] **Step 4: Check the behaviour in the console** (through the gateway or the port-forward on 8591):
  1. A table's Reconciliations tab shows a `schedule` or `settings_changed` record within one reconcile interval.
  2. Reconcile now adds a "Reconcile now" record within a minute.
  3. Inserting rows through Trino adds a `catalog_commit` record.
  4. Turning on dry run, then Reconcile now on a table with something due, records "Would start" and starts no new run. Then turn dry run off.
  5. Run maintenance in dry run still starts a run, and the record links to it. The link opens the run expanded on the Maintenance tab.
  6. The drawer reads correctly at phone width.
- [ ] **Step 5: Run `task checks:e2e-full-test KUBE_CONTEXT=retail-lakehouse`.** Expected: PASS.
- [ ] **Step 6: Report anything that differs from the spec, fix it with a failing test first, and repeat.**

### Task 13: Rebuild the cluster and test everything again

These steps are destructive: they delete and recreate the local cluster. The user asked for this step in this plan (2026-11-10).

- [ ] **Step 1: Run `task offboard`, then `limactl disk delete colima-<profile>`.** Without the second command the next onboard fails with `K8S_APISERVER_MISSING`; see project memory.
- [ ] **Step 2: Run `task onboard KUBE_CONTEXT=retail-lakehouse`.** Expected: it completes, and `task apps:validate KUBE_CONTEXT=retail-lakehouse` passes.
- [ ] **Step 3: Run the full round:**
  - `task pre-pr`;
  - `task checks:smoke-test KUBE_CONTEXT=retail-lakehouse`;
  - `task checks:e2e-full-test KUBE_CONTEXT=retail-lakehouse`;
  - Task 12 step 4 again by hand.

  Expected: all pass.
- [ ] **Step 4: Report the results.** No commit unless something had to change. Pushing waits for the user.
