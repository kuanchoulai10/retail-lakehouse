# Code Quality Batch 1 (KCL-110, KCL-100, KCL-101) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare needs-attention marks by a typed policy target, delete every branch that exists only for data or workflow histories an older program wrote, make an aggregate's state changeable only through its own methods (its id not at all), and write down that a table is referred to long-term by its Iceberg UUID.

**Architecture:** KCL-110 replaces `AppliedPolicyRef.target: dict` with the shared `PolicyTarget` value object, then removes the compatibility code in five independent slices (Temporal patches, maintenance-workflow inputs, reconciliation-workflow inputs, attempt sizes, SQL readers, the pod selector), each with its tests. KCL-100 freezes `Entity.id` at runtime and adds an AST architecture test that forbids services and adapters from assigning other objects' attributes or calling their private methods. KCL-101 is a new ADR 0014 plus links. The batch ends with one cluster rebuild.

**Tech Stack:** Python 3.13, Pydantic v2, Temporal Python SDK 1.34, SQLAlchemy, pytest, import-linter; React/orval console for the one API field change.

**Spec:** Linear KCL-110 (description), KCL-100 (description plus the 2026-11-23 scope comment), KCL-101 (description). The compatibility inventory is `/Users/kcl/.claude/jobs/ffac9ee8/tmp/kcl110-compat-inventory.md`; tasks below cite its item ids (1a, P5, H3, …), and its rows carry the exact lines and test names.

## Global Constraints

- Backend commands: `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend <tool>`; never bare `python`/`pytest`; never `cd`.
- Every commit passes `pytest -v`, `ty check`, `ruff check .`, `lint-imports` (backend); the batch ends with `task gates:pre-pr` green. Never `--no-verify`. Never run two test suites at once.
- TDD: write the failing test, run it and see it fail, then the code. A deletion task proves itself by the remaining suite staying green after the compat tests are deleted.
- **Mutation testing (user request, 2026-11-23):** every task that changes backend source ends with `task -d /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend mutation-test MUTANTS='<glob>'` (Task 0) over each module it changed, for example `MUTANTS='context.table_maintenance.application.domain.model.table.*'`. Every surviving mutant gets a test that kills it, written the TDD way (the new test fails against the mutant, passes against the code), or one line in the task report saying why it is equivalent (no input can tell it apart). Report killed / survived / equivalent counts per task. Code mutmut does not mutate (the architecture checkers in `tests/`) gets hand-run mutants in a copy under `/Users/kcl/.claude/jobs/ffac9ee8/tmp/`.
- Tests are written to be complete, not minimal: each rule a task touches gets its boundary values and each branch its own test, so the mutation step finds little.
- Development rule (decided 2026-11-22): no compatibility code, no `workflow.patched`, rebuild after the change. Nothing in this plan adds a fallback for old data.
- One object per file, `from __future__ import annotations`, ABC over Protocol, StrEnum; match the surrounding docstring style; no explanatory comments in YAML.
- Commits: conventional (`refactor(table-maintenance): …`, `feat(base): …`, `docs(adr): …`), `git add` explicit paths, message ends with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. Work stays local on `main` (as the previous batches); never push.
- Do not edit a web DTO docstring unless the published description should change (contract test).
- Hands off: `.claude/`, `platform/30-thanos`, `platform/24-e2e-validation`, ArgoCD paths. Never `sops`, never `kubectl patch configmap`.

## Rulings made while planning

- **`add_missing_columns` / `add_missing_indexes` stay** (inventory section 8). They let a `helm upgrade` add a column to a running cluster's database; whether to drop them is a workflow decision for the user, asked at plan review. The NOT NULL changes in Task 6 do not need them gone: the columns already exist in every database, so nothing is added.
- **The API `size` becomes non-null** (inventory 1g), with the generated client and the console's null branch, since the domain no longer has a None size.
- **NOT COMPAT items stay** (7c, 7g, 9, H8–H10, the Polaris and callback readers). ADR 0010's tolerant reader (ignore unknown keys) stays: it is about unknown keys, not defaults for an older writer.
- **Architecture test exemption:** `<x>.state.<attr> = …` is allowed in adapters (Starlette's `State` is the framework's attribute bag, used by `register_routes.py`); nothing else.

## Review Focus

1. A needs-attention mark set under a namespace target whose stored dict lacks `table_uuid` must not be lifted when the same policy applies again with `"table_uuid": None` — Task 1 pins it.
2. A maintenance run that times out, goes missing, is cancelled, or OOM-retries must still fence and retry exactly as today once the patches are gone — Task 2's current-history replay plus the existing scenario tests.
3. A reconciliation with a run in flight across continue-as-new must still carry its start time and workflow id and give up on the same bound — Task 4's rebuilt helpers.
4. Pydantic construction, `model_validate`, `from_primitives`, `_assign_together` without `id`, and the SQL repos' reads must not trip the frozen id — Task 9.
5. The architecture test must not flag `self.x = …`, local variables, dataclass-free builders, or `app.state.x`, and must flag `table.status = …`, `run.attempts += …` and `obj._assign_together(…)` — Task 10's mutants.

---

## Setup

### Task 0: mutmut for the backend

Done during planning and verified (`mutmut run "base.entity*"`: about 2 minutes; it found 5 survivors in `base/entity.py` and `entity_id.py`, which Task 9 kills).

**Files:**
- Modify: `src/data-platform/backend/pyproject.toml` (dev dependency `mutmut>=3.8.1`; `[tool.mutmut]` with `source_paths = ["base", "context", "shared_kernel"]`, `also_copy = ["bootstrap", "entrypoint.py", "openapi.json", ".importlinter"]`, `pytest_add_cli_args = ["-q", "-p", "no:cacheprovider", "--ignore=tests/architecture"]`: the architecture tests read the source tree, which mutmut rewrites with trampolines), `uv.lock`, `.gitignore` (`mutants/`), `src/data-platform/backend/tests/conftest.py` (under mutmut, `SandboxRestrictions.default.passthrough_modules.add("mutmut")`, so the sandboxed workflows see the active mutant and the import touches no restricted call), `src/data-platform/backend/Taskfile.yml`, `src/data-platform/backend/CLAUDE.md`, root `CLAUDE.md` (the task-name list gains the backend's `mutation-test`)

- [ ] **Step 1:** Add to the backend `Taskfile.yml`:

```yaml
  mutation-test:
    desc: "Run mutmut over the mutants whose names match MUTANTS (a module glob) and list the survivors"
    requires:
      vars: [MUTANTS]
    cmds:
      - uv run mutmut run "{{.MUTANTS}}"
      - uv run mutmut results | grep -E "survived|timeout|suspicious|segfault" || true
```

It is in no gate yet (a whole-backend run takes hours); the user decides later whether `nightly` runs it.
- [ ] **Step 2:** Backend `CLAUDE.md`, a short "Mutation testing" paragraph after Rules: the task, the glob, that `mutants/` is a throwaway copy, why architecture tests are skipped and why `mutmut` passes through the sandbox.
- [ ] **Step 3:** Verify: `task -d …/backend mutation-test MUTANTS='base.entity*'` lists survivors; `task -d …/backend unit-test` stays green (mutmut is not a pytest plugin, so the conftest block is inert in a normal run); `ty check`, `ruff check .`.
- [ ] **Step 4: Commit** `build(backend): mutation testing with mutmut`.

## KCL-110

### Task 1: Typed policy target in the needs-attention marks

**Files:**
- Modify: `context/table_maintenance/application/domain/model/table/applied_policy_ref.py`, `application/domain/model/table/operation_state.py` (docstring only if needed), `application/service/shared/applied_policy_ref_of.py`, `application/service/table_maintenance_run/record_table_maintenance_operation_result.py` (`_planned_policy`), `application/service/table_reconciliation/record_table_reconciliation.py` (`_policy_target`), `application/service/shared/__init__.py`, `application/port/outbound/table/__init__.py` (export `PolicyTarget` if the row mapper needs it), `adapter/outbound/table/sql/table_row_mapper.py` (`_encode_attention` / `_decode_attention`)
- Create: `application/service/shared/policy_target_of.py`
- Test: `tests/context/table_maintenance/application/domain/model/table/` (operation state / table attention tests), `tests/.../application/service/shared/test_policy_target_of.py`, `tests/.../adapter/outbound/table/test_tables_sql_repo.py`

(Paths under `context/` and `tests/` are relative to `src/data-platform/backend/`.)

**Interfaces:**
- Produces: `AppliedPolicyRef.target: PolicyTarget | None` (None = platform default). `policy_target_of(raw: dict[str, Any] | None) -> PolicyTarget | None` in `application/service/shared`, raising the application `ValidationError("invalid policy target …")` on a malformed dict (the message `record_table_reconciliation._policy_target` uses today). `applied_policy_ref_of` and `_planned_policy` build the target with it; `record_table_reconciliation` uses it instead of its private `_policy_target`.
- Ports keep `dict[str, Any] | None` (`policy_target` fields of plan output and record input): the conversion happens in the service.

- [ ] **Step 1: Write the failing tests**
  - Domain: `test_a_mark_holds_under_the_same_target_spelled_differently` — two `AppliedPolicyRef`s for the same namespace target, one built from `{"type": "namespace", "path": ["c", "n"]}` and one from `{"type": "namespace", "path": ["c", "n"], "table_uuid": None}` via `PolicyTarget.from_primitives`; `OperationState(attention=AttentionMark(policy=first, …)).needs_attention_under(second)` is True, and `Table.lift_attention_set_under_another_policy(second, at)` returns `[]`.
  - Domain: `test_a_mark_is_lifted_under_another_target` — same policy id and version, target `["c", "n"]` vs `["c", "m"]`: lifted.
  - Service: `test_policy_target_of_reads_a_target_and_refuses_a_malformed_one` — `None → None`; the namespace dict → `PolicyTarget(type=NAMESPACE, path=("c", "n"))`; `{"type": "table", "path": ["c", "n", "t"]}` (no uuid) raises `ValidationError` matching `invalid policy target`.
  - SQL: extend the attention round-trip test so a mark with a table target and one with the default (`None`) both read back equal to what was written.
- [ ] **Step 2: Run them; the domain test fails** (`AppliedPolicyRef(target=PolicyTarget…)` is refused: the field is a dict) and `policy_target_of` does not exist.
- [ ] **Step 3: Implement.** Field type change; `policy_target_of` as above; row mapper writes `mark.policy.target.to_primitives()` (or None) and reads `PolicyTarget.from_primitives(...)`; fix every test builder that passes a dict target.
- [ ] **Step 4: Run** the table-maintenance domain, service and `adapter/outbound/table` tests: PASS. Then the full backend suite, `ty check`, `ruff check .`, `lint-imports`.
- [ ] **Step 5: Mutation step** over `context.table_maintenance.application.domain.model.table.*`, `context.table_maintenance.application.domain.model.shared.policy_target*`, `context.table_maintenance.application.service.shared.*` and `context.table_maintenance.adapter.outbound.table.sql.table_row_mapper*`; kill or justify every survivor.
- [ ] **Step 6: Commit** `refactor(table-maintenance): compare needs-attention marks by a typed policy target (KCL-110)`.

### Task 2: Remove the Temporal patches and the old-history fixture

**Files:**
- Modify: `adapter/hybrid/temporal/inbound/workflows/table_maintenance_workflow.py` (P1–P5), `table_reconciliation_workflow.py` (P6–P9), `table_maintenance_attempt_policy.py` (`unfenced_operation_worst_case`)
- Delete: `tests/.../temporal/inbound/fixtures/maintenance_runs_before_waiting_for_jobs_gone.json` and the `fixtures/` directory
- Test: `tests/.../temporal/inbound/test_table_maintenance_workflow.py`, `test_table_reconciliation_workflow.py`, `test_table_maintenance_attempt_policy.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: workflows with no `workflow.patched` call. `_run_search_attributes` returns `TypedSearchAttributes` (not Optional). `_finish` always awaits `_await_jobs_gone`. `_in_flight_per_operation` always uses `operation_worst_case()`. `_mint_reconciliation_id` always uses `mint_workflow_prefixed_id("rc")`. The maintenance test module's `_run` gains `max_cached_workflows: int | None = None`, passed to `Worker`.

- [ ] **Step 1: Write the failing test** `test_current_histories_replay` in `test_table_maintenance_workflow.py`: run, with `_run(..., max_cached_workflows=0)`, one workflow that covers an OOM retry at a larger size (`record_replies` `{"failure_class": "oom", "next_step": "retry_larger", "next_size": "M"}`), a timed-out attempt, a missing job, and two runs with the jobs-gone wait between them (one scenario or a parametrized few, using the scripts listed in inventory section 6); fetch each history and `Replayer(workflows=[TableMaintenanceWorkflow]).replay_workflow(history)`. Also add `test_no_workflow_calls_patched` to `tests/architecture/test_temporal_workflow_determinism.py` (or beside it): no `workflow.patched` / `workflow.deprecate_patch` call in any file under `adapter/hybrid/temporal/inbound/workflows/`.
- [ ] **Step 2: Run them.** The architecture test fails (nine calls). The replay test fails until `_run` accepts `max_cached_workflows`.
- [ ] **Step 3: Implement.** Keep only the patched branch of P1–P9 (inventory 5.1, 5.2). Keep the `step not in (None, RETRY_SAME)` guard (P4 row: None is a failed record). Delete `unfenced_operation_worst_case` and `test_unfenced_worst_case_is_the_bound_from_before_fencing`, the fixture, `test_history_from_before_waiting_for_jobs_gone_replays` and its now-unused imports, and the marker assertion in `test_run_and_reconciliation_ids_survive_replay` (keep its replay). Rewrite the docstrings the inventory lists (5.1 and 5.2 "Docstrings to rewrite") to describe only current behaviour.
- [ ] **Step 4: Run** the two workflow test modules, the attempt-policy tests and `tests/architecture`: PASS. Full backend suite and the checks.
- [ ] **Step 5: Commit** `refactor(table-maintenance): drop the workflow patches; histories are not replayed across changes (KCL-110)`.

### Task 3: Maintenance workflow and record/submit inputs without old-writer defaults

**Files:**
- Modify: `table_maintenance_workflow.py` (1e, H1), `contracts/table_maintenance/default_start_size.py` (delete) and `contracts/table_maintenance/__init__.py`, `contracts/table_maintenance/workflow_input.py` (H7), `port/inbound/table_maintenance_run/submit_maintenance_operation/input.py` (1f), `port/inbound/table_maintenance_run/record_table_maintenance_operation_result/input.py` (7a), `service/table_maintenance_run/record_table_maintenance_operation_result.py` (7a: drop `_planned_policy`'s resolve fallback and the `resolve_applicable_policy` constructor dependency), `bootstrap/container/build_use_cases.py`, `adapter/hybrid/temporal/inbound/activities/table_maintenance_activities.py` (docstring at 81)
- Test: maintenance workflow tests (`_plan` always emits `start_size`, default `"S"`), `test_activities.py`, `test_run_activity_payloads.py`, `tests/.../temporal/contracts/test_temporal_contracts.py`, the three service test files the inventory names in 7a

**Interfaces:**
- Consumes: Task 1's `policy_target_of` (`_planned_policy` becomes `AppliedPolicyRef(policy_id=…, version=…, target=policy_target_of(request.policy_target))` plus `request.policy_name`).
- Produces: `RecordTableMaintenanceOperationResultUseCaseInput` with required `ended_by`, `still_running`, `max_attempts`, `policy_id: str`, `policy_name: str`, `policy_version: int`, `policy_target: dict[str, Any] | None` (required key). `SubmitMaintenanceOperationUseCaseInput.size: str` required. `TableMaintenanceWorkflowInput` with required `attempt_deadline_seconds`, `max_attempts`, `queue_wait_limit_seconds`. `RecordTableMaintenanceOperationResultService.__init__` without the resolve use case.

- [ ] **Step 1: Write the failing tests:** `test_record_result_input_requires_the_planned_policy` (building the input without `policy_id` raises `InvariantViolation`), `test_submit_input_requires_a_size`, `test_maintenance_workflow_input_requires_the_attempt_settings` (`TypeError` on a missing setting).
- [ ] **Step 2: Run; they fail** (defaults accept the missing keys).
- [ ] **Step 3: Implement**, then fix the helpers first (`_plan`, the service-test `_record` builders, `TableMaintenanceWorkflowInput(...)` constructions at the contract-test lines 60 and 103), and delete the compat tests the inventory lists under 1e, 1f, H1, H7 and 7a. Fix the H11 test docstring ("as before failure classes") to describe a reply without a decision.
- [ ] **Step 4: Run** the maintenance workflow, activities, payload, contract and record-service tests; then the full suite and checks: PASS.
- [ ] **Step 5: Commit** `refactor(table-maintenance): maintenance workflow and record inputs carry every key (KCL-110)`.

### Task 4: Reconciliation workflow without old-history fallbacks

**Files:**
- Modify: `table_reconciliation_workflow.py` (H2–H6), `port/inbound/table_maintenance_run/create_table_maintenance_runs/input.py` (7b `priority` required)
- Test: `test_table_reconciliation_workflow.py` (helpers `_planned`, `start_with_a_gone_child`, `start_with_an_unsignalled_run`, `h.start(in_flight_run_ids=…)`, `report_gone_child`, `_with_candidates`, `_with_next_check`), `test_activities.py` (7d)

**Interfaces:**
- Consumes: Task 2's patch-free workflow.
- Produces: a carried in-flight run always has `in_flight_started_at` and `in_flight_workflow_id` (refuse the input otherwise: `_carry`/`_start_run` set them together); plans are indexed (`plan["priority"]`, `plan["attempt_deadline_seconds"]`, …, `plan["policy_id"]`); reports indexed (`report["unapplied_raise"]`, `report["raises_received"]`).

- [ ] **Step 1: Fix the helpers to send what current code sends** (`_planned` with `priority` and the three settings; in-flight starts with `in_flight_started_at` and a workflow id; `report_gone_child` with `raises_received`; drop `_with_candidates` / `_with_next_check`). Rebuild the five "cannot be signalled" scenarios with a workflow id that does not exist and the `_run(lookup=…)` fake answering `running: True` (inventory H3). Run the module: PASS on the unchanged workflow (helpers now match reality).
- [ ] **Step 2: Write the failing test** `test_a_carried_run_in_flight_needs_its_start_time_and_workflow_id`: starting with `in_flight_run_ids` but no `in_flight_started_at` (or no workflow id) fails the workflow task with a clear error instead of inventing a deadline. Run: FAIL.
- [ ] **Step 3: Implement** H2–H6 and 7b; delete the compat tests the inventory lists under H2, H3, H5, H6 and `test_next_plan_is_one_interval_on`; drop the `"run_id"` key from 7d's payload; rewrite the class docstring lines 102–110.
- [ ] **Step 4: Run** the reconciliation module and activities tests, then the full suite and checks: PASS.
- [ ] **Step 5: Commit** `refactor(table-maintenance): reconciliation workflow reads current plans and carries only current state (KCL-110)`.

### Task 5: Every attempt has a size

**Files:**
- Modify: `domain/service/table_maintenance_run/decide_next_attempt.py` (1a), `domain/model/table_maintenance_run/operation_attempt.py` (1b), `adapter/outbound/table_maintenance_run/sql/table_maintenance_run_row_mapper.py` (1c), `service/table_maintenance_run/record_table_maintenance_operation_result.py` (1d), `domain/model/table/table.py` and `operation_state.py` (`record_operation_result` / `after_success` size and attempt required on success), the run output port and `table_maintenance_run_output_fields.py`, `adapter/inbound/web/table_maintenance_run/dto.py` (1g, `size: str`), `openapi.json`, `frontend/src/api/generated/…`, `frontend/src/components/tabs/MaintenanceRunPanel.tsx` and its stories/tests
- Test: `test_decide_next_attempt.py`, `test_table_maintenance_runs_sql_repo.py`, table domain tests, the panel tests

**Interfaces:**
- Produces: `decide_next_attempt(failure_class, size: ComputeSize, attempt, max_attempts, *, still_running=False)`; `OperationAttempt.size: ComputeSize`; API attempt `size: string`.

- [ ] **Step 1: Write the failing tests:** `test_an_attempt_needs_a_size` (`OperationAttempt(size=None, …)` raises `InvariantViolation`); a run-mapper test that a stored attempt without the `size` key raises `KeyError` instead of reading None; the panel test renders the size without a null branch (adjust the existing test to drop the "no size" case).
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** In `RecordTableMaintenanceOperationResultService.execute`, an attempt that never started (`run.attempt_record(...)` is None) raises the same `InvalidRunTransition` before `decide_next_attempt` runs. `_decode_attempt` indexes every key (`data["job_name"]` etc.; None values stay legal). Delete `test_attempt_without_a_size_counts_as_s` and rework `test_attempt_without_a_running_time_decodes_to_none` (keys present, None values). Regenerate the API: run the backend task that writes `openapi.json` and the frontend orval generation (find them in `src/data-platform/backend/Taskfile.yml` and `src/data-platform/frontend/package.json`).
- [ ] **Step 4: Run** the backend suite and checks, then `task -d /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend unit-test` and the contract test (`task gates:pre-pr` runs it; or the contract task it names): PASS.
- [ ] **Step 5: Commit** `refactor(table-maintenance): every attempt has a size (KCL-110)`.

### Task 6: SQL readers read only what current writers write

**Files:**
- Modify: `adapter/outbound/table/sql/table_row_mapper.py` (2a–2e), `tables_table.py` (`matched_policy_id`, `matched_policy_version`, `priority`, `over_target_partitions_json` → `nullable=False`), `table_maintenance_run/sql/table_maintenance_run_row_mapper.py` and `table_maintenance_runs_table.py` (3a), `table_reconciliation/sql/table_reconciliation_row_mapper.py` (3c)
- Test: `test_tables_sql_repo.py`, `test_table_maintenance_runs_sql_repo.py`, `test_create_schema.py`, `test_catalog_discoveries_sql_repo.py`

**Interfaces:** none new.

- [ ] **Step 1: Write the failing test** `test_tables_columns_current_writers_always_fill_are_not_null`: inspect `tables_table` / `table_maintenance_runs_table` metadata and assert the five columns above are `nullable=False`. Run: FAIL.
- [ ] **Step 2: Implement.** Index keys directly, drop `_ATTENTION_POLICY_KEYS`, the `or TablePriority.default()` reads and the None branches. Delete the compat tests the inventory lists under 2a–2f, 3a and section 8 that simulate an older database through `create_all`/`add_missing_columns` (`…stored_before_matches…`, `…older_shape_is_refused…`, `…without_a_priority_reads_as_p3` ×2, `…null_over_target_column…`, `…operation_state_without_new_keys…`, `…stored_before_the_two_times…`, `test_create_schema_adds_columns_an_older_release_did_not_create`, `test_create_schema_leaves_the_legacy_discovery_rule_tables_in_place`, `test_an_older_catalog_discoveries_table_gains_the_failure_columns`, and reword `test_migrate_adds_the_discovery_policy_tables_to_an_older_database` as an idempotence test). Keep `test_add_missing_columns.py` and `test_add_missing_indexes.py` (ruling above).
- [ ] **Step 3: Run** the outbound SQL tests, `tests/bootstrap`, then the full suite and checks: PASS.
- [ ] **Step 4: Commit** `refactor(table-maintenance): SQL readers read only what current writers write (KCL-110)`.

### Task 7: Find an attempt's pods by its labels only

**Files:**
- Modify: `adapter/outbound/table_maintenance_run/k8s/list_maintenance_job_pods.py`, `read_maintenance_job_pods_k8s_gateway.py` (docstring)
- Test: `test_read_maintenance_job_pods_k8s_gateway.py`, `test_read_maintenance_job_evidence_k8s_gateway.py`

- [ ] **Step 1: Rewrite** `test_read_pods_selects_the_attempt_by_its_labels_and_by_its_application` as `test_read_pods_selects_the_attempt_by_its_labels` expecting exactly one `list_namespaced_pod` call with the attempt-label selector. Run: FAIL (two calls).
- [ ] **Step 2: Implement** one selector; delete the operator-label tests and `OPERATOR_SELECTOR` / `by_operator` from the fakes (inventory 4).
- [ ] **Step 3: Run** the k8s adapter tests, full suite and checks: PASS.
- [ ] **Step 4: Commit** `refactor(table-maintenance): find an attempt's pods by its labels only (KCL-110)`.

### Task 8: Write the development rule down

**Files:**
- Modify: `src/data-platform/backend/CLAUDE.md` (Rules: a new bullet "**No compatibility code during development.** A change to stored data, a payload or workflow behaviour ships without fallbacks for old data, without `workflow.patched`, and with a cluster rebuild; `tests/architecture/…::test_no_workflow_calls_patched` guards the patches." and drop the line-70 parenthesis), `docs/agents/known-follow-ups.md` (inventory section 10 lines), `docs/adr/0002-entity-workflow-per-table.md` (one sentence: during development the cluster is rebuilt instead of patching), `docs/agents/project-history.md` (one 2026-11-23 KCL-110 line)

- [ ] **Step 1:** Edit the docs; `grep -rn "workflow.patched\|patch \`" src/data-platform/backend/CLAUDE.md docs/agents/known-follow-ups.md` shows only the new rule.
- [ ] **Step 2: Commit** `docs(table-maintenance): no compatibility code during development (KCL-110)`.

## KCL-100

### Task 9: An entity's id cannot change

**Files:**
- Modify: `src/data-platform/backend/base/entity.py`
- Test: `tests/base/test_entity.py`, `tests/base/test_entity_assign_together.py`

**Interfaces:**
- Produces: `Entity.id` declared `id: ID = Field(frozen=True)` (Pydantic raises `frozen_field`, which `_refusing_frozen_changes` turns into `AttributeError("<Class> is immutable")`); `_assign_together` raises `AttributeError(f"{type(self).__name__} is immutable")` when `"id"` is among the changes, whatever its value, before rebuilding.

- [ ] **Step 1: Write the failing tests:** `test_the_id_cannot_be_reassigned` (`user.id = UserId("2")` raises `AttributeError` matching `is immutable`; `user.id` unchanged; `user.name = "b"` still works); `test_assign_together_refuses_the_id` (also with the same id value); `test_construction_and_validation_still_set_the_id` (`User(id=…)`, `User.model_validate({...})`, `User.from_primitives`-style wire path if `Entity` has one).
- [ ] **Step 2: Run; the first two fail** (assignment succeeds).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `tests/base`, then the full backend suite (every repo round-trip builds entities) and checks: PASS.
- [ ] **Step 5: Mutation step** over `base.entity*` and `base._invariant_guarded_model*`. The Task 0 trial already shows five survivors to kill or justify: `Entity.__pydantic_init_subclass__` mutant 3, `Entity.__hash__` mutant 1 (hashing is not pinned to the id), `Entity._assign_together` mutants 7 and 8, and `EntityId.__pydantic_init_subclass__` mutant 9 (`mutmut show <name>` prints each diff).
- [ ] **Step 6: Commit** `feat(base): an entity's id cannot change after creation (KCL-100)`.

### Task 10: Aggregates change only through their own methods

**Files:**
- Create: `src/data-platform/backend/tests/architecture/test_state_changes_through_methods.py`
- Modify: `src/data-platform/backend/CLAUDE.md` (Rules bullet and the `Entity[ID]` line: "its `id` cannot change after creation")

**Interfaces:**
- Consumes: `tests.architecture.contexts` (`BACKEND`, `context_dir`, `context_names`), as `test_no_infrastructure_terms.py` does.
- Produces: two parametrized-by-file tests over every `.py` under each context's `application/service/` and `adapter/`:
  - `test_services_and_adapters_assign_only_their_own_attributes`: an `ast.Assign` / `AugAssign` / `AnnAssign` / `Delete` target that is an `ast.Attribute` (at any depth, including tuple targets and subscripts of attributes like `run.attempts[0] = …`) must have `self` or `cls` as its root name, except an `<expr>.state.<attr>` target (Starlette app state).
  - `test_services_and_adapters_call_no_private_method_of_another_object`: an `ast.Call` whose func is an `ast.Attribute` with a name starting with one `_` (not a dunder) must be on `self`, `cls` or `super()`.
  - Failure messages name file, line and the offending expression.

- [ ] **Step 1: Write the tests, plus a self-check** `test_the_checks_flag_what_they_forbid` that feeds the two checker functions source snippets: flagged — `table.status = x`, `run.attempts += (a,)`, `a.b.c = 1`, `t._assign_together(id=x)`; not flagged — `self._repo = repo`, `x = 1`, `app.state.use_cases = u`, `super()._f()`, `self._f()`.
- [ ] **Step 2: Run.** The self-check passes once the checkers exist; the scan over the real code is expected to PASS (the 2026-11-23 search found no violation). If it finds one, fix the code by moving the change into an aggregate method, TDD as usual, in this task.
- [ ] **Step 3: Hand mutants** (mutmut does not mutate `tests/`): allow any root name; drop `AugAssign`; allow `_`-calls on any object; drop the subscript case. Each must make the self-check fail. Report.
- [ ] **Step 4:** CLAUDE.md edits; full backend suite and checks: PASS.
- [ ] **Step 5: Commit** `test(architecture): aggregates change only through their own methods (KCL-100)`.

## KCL-101

### Task 11: ADR 0014, a table is referred to by its Iceberg UUID

**Files:**
- Create: `docs/adr/0014-long-lived-references-to-a-table-use-its-uuid.md`
- Modify: `docs/adr/0001-table-identity-by-iceberg-uuid.md` (Consequences: one line linking 0014), `0005-bounded-contexts-and-context-map.md` (cross-context references: link 0014), `0011-prefixed-resource-ids.md` ("Unchanged ids": link 0014), `src/data-platform/backend/CLAUDE.md` (Bounded Contexts, after "links to other contexts by identifier values": "a table by its Iceberg table UUID (ADR 0014)"), `docs/agents/project-history.md`

- [ ] **Step 1: Verify the facts** against the upstream specs (Iceberg REST OpenAPI `open-api/rest-catalog-open-api.yaml`, Polaris management API `spec/polaris-management-service.yml`, at the versions the cluster runs): no namespace rename, no catalog rename. Record the spec URLs and the endpoints that exist (`POST /namespaces/{ns}/properties`, `PUT /catalogs/{name}` with no name field).
- [ ] **Step 2: Audit stored references.** For every SQL table, Kafka payload and Temporal input in `context/`: list how it refers to a table (UUID / path / display copy). Any long-lived reference by path that is not a display copy goes in the ADR's Consequences and gets a new Linear issue (project 程式碼品質與架構, label Improvement, six sections per `docs/agents/linear-issues.md`).
- [ ] **Step 3: Write ADR 0014** in the style of 0013 (Date 2026-11-23, Status Accepted, Context, Considered options, Decision, Consequences). Decision: long-lived references (stored rows, cross-context messages, events) use the Iceberg table UUID; paths are for lookup, display and URLs; a catalog and a namespace have no UUID, their path is their identity, and deleting one and creating another with the same name is the same catalog or namespace again (a policy attached there applies to the new one). Consequences include the audit result, the access context note (Polaris grants by name; the access context will decide against this ADR), and "no architecture test: whether a stored field is a path is not statically decidable".
- [ ] **Step 4: Commit** `docs(adr): long-lived references to a table use its Iceberg UUID (KCL-101)`.

## Batch close

### Task 12: Rebuild and verify

- [ ] **Step 1:** `task gates:pre-pr` from the repo root: exit 0.
- [ ] **Step 2:** `task -y offboard KUBE_CONTEXT=retail-lakehouse`, `task -y onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts`, `task apps:validate KUBE_CONTEXT=retail-lakehouse` (the rebuild also removes `kcl71_noaccess`).
- [ ] **Step 3: Verify on the cluster** (Trino is paused; write with PyIceberg from the API pod, installing `pyiceberg-core` in the pod for the session): attach a managing discovery policy, create a partitioned table, see it managed; start a manual run of each operation and see each run `succeeded` with a size on every attempt; see the reconciliation record with its typed policy target; worker logs free of nondeterminism and `KeyError`. A needs-attention mark cannot be set on the cluster without an OOM at L, so check instead that `GET /v1/tables/{uuid}` reads every operation state; Task 1's tests cover the mark. Write the report to `/Users/kcl/.claude/jobs/ffac9ee8/tmp/batch-1-verify-report.md`.
- [ ] **Step 4: Linear:** a dated Traditional Chinese comment on KCL-110, KCL-100 and KCL-101 with what landed (commits) and the verification result; move each to Done; update the project table rows for KCL-110 and KCL-100 if the rule now has a test.
