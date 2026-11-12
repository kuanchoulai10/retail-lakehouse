# Milestone 2: failure classes, sizes and OOM escalation — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task (you are the milestone implementer; do not dispatch subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every maintenance attempt runs at a size S / M / L and records it; every failed attempt is classified (`oom`, `timeout`, `commit_conflict`, `permanent`, `cancelled`, `other`) with its raw error and whether its Spark event log finished; an `oom` retries at the next size, and an `oom` at L stops and marks that table's operation **needs attention**; each table starts at the size of its last successful run and steps down when measured use stays low; the console shows every attempt with its size, result, reason, event log state and what the platform does next.

**Architecture:** the decision lives in the domain, not in the workflow. Two pure domain services classify a failed attempt from its evidence and decide the next attempt. The existing `record_maintenance_operation_result` activity becomes the one place that reads the evidence (pod and SparkApplication status through a new Kubernetes gateway, the event log marker through a new object-store gateway), classifies, decides, records the attempt on the run and the outcome on the table, and returns the decision. The maintenance workflow passes how the attempt ended and follows the returned decision; it gains no new command, so running histories replay. The size is chosen by the plan (the table's remembered size) and turned into memory only by the SparkApplication manifest, from settings.

**Tech stack:** Python 3.14, temporalio, kubernetes client, pyarrow (`pyarrow.fs.S3FileSystem`, already a dependency), FastAPI, SQLAlchemy JSON columns (no DDL), PySpark runtime, React console (Vitest, Storybook), Helm.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` ("Correctness", "2. Failure classes and OOM", "Finding a table's workflows in the Temporal UI", "Verification and rebuilds"). Linear issues KCL-48 (sizes), KCL-49 (classes), KCL-50 (escalation), KCL-51 (remembered size, step-down), KCL-52 (console).

## Global Constraints

- Project rules in `CLAUDE.md`, `src/data-platform/backend/CLAUDE.md` and `src/data-platform/frontend/CLAUDE.md` hold: one object per file, descriptive file names, `__init__.py` re-exports, `from __future__ import annotations`, ABC ports, StrEnum, `{Verb}{Noun}Gateway` with verbs from the approved list (only `Read` is used here), no infrastructure words in `application/` identifiers (say `execution_id`, never `spark_application_id`), hybrid contracts import only stdlib / base / ports, adapters see only ports.
- Sizes, verbatim (`ComputeSize` values `"S"`, `"M"`, `"L"`; default start size `S`). Cores stay 1 / `coreLimit: "1"`; memory overhead stays Spark's default (`max(384Mi, 0.4 × memory)` for a Python application on Kubernetes):

  | Size | driver memory | executor memory | executors | pod requests, driver + executor |
  |---|---|---|---|---|
  | S | `768m` | `768m` | 1 | 1152Mi + 1152Mi = 2304Mi |
  | M | `1g` | `1536m` | 1 | 1434Mi + 2150Mi = 3584Mi |
  | L | `1536m` | `2g` | 1 | 2150Mi + 2867Mi = 5017Mi |

  The node (`kubectl describe node --context retail-lakehouse`, 2026-11-13) has 25994Mi allocatable and 20032Mi requested, so about 5960Mi is free: one L job fits alone; L next to any other Spark job does not, and the second job stays Pending until memory frees (its attempt clock keeps running). Two S jobs (the admission limit) fit. Today's single size was 1g / 1g (2868Mi), so most jobs get smaller.
- Failure classes, verbatim: `oom`, `timeout`, `commit_conflict`, `permanent`, `cancelled`, `other`.
- Attempt endings (how the workflow saw the attempt end), verbatim: `result` (Spark's callback), `job_failed` (polled FAILED), `timed_out`, `missing`, `cancelled`, `submit_failed`, `admission_failed`.
- Next steps, verbatim: `done`, `retry_larger`, `retry_same`, `needs_attention`, `attempts_used`, `not_retried`, `cancelled`, `still_running`.
- OOM signals: a driver or executor container whose terminated reason is `OOMKilled`, or whose exit code is `137`; an executor exit code `52` (Spark's own exit code for a JVM `OutOfMemoryError`); any of the texts `java.lang.OutOfMemoryError`, `OOMKilled`, `exit code 52` in the callback error, the SparkApplication error or a driver termination message. Container exit codes count only for endings `result` and `job_failed`: a pod the platform deleted (timeout, cancel, missing job) also dies with 137.
- The attempt policy is unchanged: 3 attempts, backoffs 60 s and 120 s, fencing as in milestone 1. "Less work per attempt" is **deferred to milestone 3** (KCL-55's top-N): until partition candidates exist there is nothing to shrink, and a hook with nothing behind it would be dead code. `NextAttempt` is where milestone 3 adds the partition limit.
- The milestone 1 search attributes are untouched: no workflow start changes, `test_maintenance_run_carries_table_search_attributes` and the reconciliation search-attribute tests must pass unchanged.
- No new workflow command on a path a running history can reach. The workflow only reads a new key of an activity result it already records; a result without the key behaves as today. If an implementation does add a command, guard it with `workflow.patched("classify-attempt-failure")`.
- Persistence stays in the existing JSON columns (`table_maintenance_runs.operations_json`, `tables.operation_states_json`); every new key decodes with a default, so rows written before this milestone load unchanged.
- Test commands: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest <path> -v`; before each commit also `ty check`, `ruff check .`, `lint-imports` the same way. Spark runtime: `uv run --project src/data-platform/runtime/spark --directory src/data-platform/runtime/spark pytest -v`. Console: `npm --prefix src/data-platform/frontend run test -- <file>` and `npm --prefix src/data-platform/frontend run test:stories`.
- Post a comment (Traditional Chinese, plain words) on the issue a task concerns when it lands, when you decide something this plan leaves open, and when you are blocked.

## Review Focus

1. **The platform's own kill looks like an OOM.** Fencing and cancel delete pods, which then exit 137. A `timed_out` or `cancelled` attempt with exit-137 containers must classify `timeout` / `cancelled`, never `oom`. Tests `test_timed_out_attempt_is_timeout_even_with_exit_137` and `test_exit_137_counts_only_for_result_and_job_failed` in Task 1.
2. **The evidence is gone before it is read.** Spark deletes failed executor pods, and `_finish` deletes the SparkApplication. Executors are kept (`spark.kubernetes.executor.deleteOnTermination=false`, Task 6 `test_executor_pods_are_kept_after_they_end`), the classification runs inside the record activity, which every failed attempt reaches before any delete (Task 10 `test_failed_attempt_is_recorded_before_its_job_is_deleted`), and unreadable evidence still records the attempt from its error text (Task 9 `test_unreadable_evidence_still_records_the_attempt`).
3. **A retried record activity decides twice.** A record that reached the database but lost its reply is retried; the second call must return the stored decision and read nothing, or a needs-attention mark could be set on a run that was then told to retry. Task 9 `test_replayed_record_returns_the_stored_decision`.
4. **A running history replayed by the new worker.** Histories recorded before this milestone hold record results without `next_step`; they must replay and keep today's three same-size attempts. Task 10 `test_history_from_before_failure_classes_replays` and `test_record_result_without_a_decision_keeps_retrying_at_the_same_size`.
5. **Needs attention stops too much or too little.** It blocks only that operation of that table, only under the applicable policy it was set under; a manual run or a policy change clears it, a scheduled reconcile does not. Task 4 `test_manual_run_clears_needs_attention_of_its_operations` and Task 5 `test_needs_attention_blocks_only_its_operation_under_the_same_policy`, `test_a_changed_applicable_policy_lifts_needs_attention`.

All backend paths below are under `src/data-platform/backend/`, and `context/…` means `context/table_maintenance/…`. Tests mirror the source path under `tests/context/table_maintenance/`.

---

### Task 1: sizes, failure classes and the classifier (domain)

**Files:**
- Create: `application/domain/model/shared/compute_size.py`; export from `domain/model/shared/__init__.py`
- Create in `application/domain/model/table_maintenance_run/`: `failure_class.py`, `attempt_ending.py`, `container_exit.py`, `failure_evidence.py`; export from that package
- Create: `application/domain/service/table_maintenance_run/__init__.py`, `classify_attempt_failure.py`
- Test: `tests/…/application/domain/model/shared/test_compute_size.py`, `tests/…/application/domain/service/table_maintenance_run/test_classify_attempt_failure.py`

**Interfaces:**
- `ComputeSize(StrEnum)`: `S = "S"`, `M = "M"`, `L = "L"`; `larger() -> ComputeSize | None`; `smaller() -> ComputeSize | None`.
- `FailureClass(StrEnum)`: `OOM = "oom"`, `TIMEOUT = "timeout"`, `COMMIT_CONFLICT = "commit_conflict"`, `PERMANENT = "permanent"`, `CANCELLED = "cancelled"`, `OTHER = "other"`.
- `AttemptEnding(StrEnum)`: the seven endings in Global Constraints (`RESULT = "result"`, …).
- `ContainerExit(ValueObject)`: `role: str` (`"driver"` / `"executor"`), `reason: str | None`, `exit_code: int | None`, `message: str | None`.
- `FailureEvidence(ValueObject)`: `ended_by: AttemptEnding`, `texts: tuple[str, ...] = ()`, `containers: tuple[ContainerExit, ...] = ()`.
- `classify_attempt_failure(evidence: FailureEvidence) -> FailureClass`, first rule that holds: `timed_out` → `timeout`; `cancelled` → `cancelled`; an OOM container signal (only for `result` / `job_failed`) or an OOM text → `oom`; a text containing `NoSuchTableException`, `ForbiddenException` or `NotAuthorizedException` → `permanent`; a text containing `CommitFailedException` → `commit_conflict`; else `other`. The runtime's "no file group was committed" message stays `other`: with partial progress on, a group can fail from an OOM or a conflict, and both retry at the same size unless the container evidence says OOM.

- [ ] **Step 1: Failing tests.**
  - `test_sizes_step_up_and_down`: `S.larger() is M`, `M.larger() is L`, `L.larger() is None`, `S.smaller() is None`, `L.smaller() is M`.
  - `test_oom_killed_executor_is_oom` (`result`, executor reason `OOMKilled`); `test_exit_52_executor_is_oom`; `test_exit_137_driver_is_oom` (`job_failed`).
  - `test_out_of_memory_error_text_is_oom` (`result`, text `"Py4JJavaError: … java.lang.OutOfMemoryError: Java heap space"`); `test_oom_killed_in_the_job_error_is_oom` (text `"driver container failed with ExitCode: 137, Reason: OOMKilled"`).
  - `test_timed_out_attempt_is_timeout_even_with_exit_137`; `test_cancelled_attempt_is_cancelled_even_with_exit_137`.
  - `test_exit_137_counts_only_for_result_and_job_failed`: `missing` with an exit-137 executor and no text → `other`.
  - `test_commit_failed_is_commit_conflict`; `test_missing_table_is_permanent`; `test_oom_wins_over_commit_conflict` (both texts → `oom`).
  - `test_partial_progress_with_nothing_committed_is_other`; `test_unknown_error_is_other`.
- [ ] **Step 2: Run them; they fail** (missing modules).
- [ ] **Step 3: Implement.** The text patterns are module constants of `classify_attempt_failure.py`.
- [ ] **Step 4: Run the tests and all four checks; they pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): classify why a maintenance attempt failed`.

### Task 2: deciding the next attempt (domain)

**Files:**
- Create in `domain/model/table_maintenance_run/`: `next_step.py`, `next_attempt.py`
- Create: `domain/service/table_maintenance_run/decide_next_attempt.py`
- Test: `tests/…/domain/service/table_maintenance_run/test_decide_next_attempt.py`

**Interfaces:**
- `NextStep(StrEnum)`: the eight next steps in Global Constraints.
- `NextAttempt(ValueObject)`: `step: NextStep`, `size: ComputeSize | None` (set iff `step` is `retry_larger` or `retry_same`).
- `decide_next_attempt(failure_class: FailureClass, size: ComputeSize | None, attempt: int, max_attempts: int, *, still_running: bool = False) -> NextAttempt`. A `None` size (an attempt started before sizes existed) counts as S. In order: `still_running` → `still_running`; `cancelled` → `cancelled`; `permanent` → `not_retried`; `oom` with no larger size → `needs_attention`; `attempt >= max_attempts` → `attempts_used`; `oom` → `retry_larger` at the next size; anything else → `retry_same` at the same size.

- [ ] **Step 1: Failing tests.**
  - `test_oom_at_s_retries_at_m`, `test_oom_at_m_retries_at_l`.
  - `test_oom_at_l_needs_attention_even_on_the_last_attempt` (`L`, attempt 3 of 3 → `needs_attention`, size `None`).
  - `test_oom_at_m_on_the_last_attempt_uses_up_the_attempts`.
  - `test_timeout_conflict_and_other_retry_at_the_same_size` (parametrised over the three; `M` → `retry_same`, `M`).
  - `test_last_attempt_of_a_same_size_failure_uses_up_the_attempts`.
  - `test_permanent_is_not_retried`, `test_cancelled_stops`, `test_still_running_stops_whatever_the_class`.
  - `test_attempt_without_a_size_counts_as_s` (`oom`, `None` → `retry_larger`, `M`).
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): decide the next attempt from the failure class and size`.

### Task 3: the run keeps every attempt

**Files:**
- Create: `domain/model/table_maintenance_run/operation_attempt.py`; modify `operation_run.py`, `table_maintenance_run.py`, the package `__init__.py`
- Modify: `adapter/outbound/table_maintenance_run/sql/table_maintenance_run_row_mapper.py`; `application/service/table_maintenance_run/table_maintenance_run_output_fields.py`; re-export the new types from `port/outbound/table_maintenance_run/__init__.py` as the mapper needs
- Test: `test_table_maintenance_run.py`, `test_table_maintenance_run_row_mapper.py`, the get / list runs service tests

**Interfaces:**
- `OperationAttempt(ValueObject)`: `attempt: int`, `size: ComputeSize | None`, `status: OperationRunStatus` (running / succeeded / failed), `started_at: datetime`, `finished_at: datetime | None = None`, `failure_class: FailureClass | None = None`, `error: str | None = None`, `event_log_finished: bool | None = None`, `next_step: NextStep | None = None`, `next_size: ComputeSize | None = None`.
- `OperationRun.attempt_history: tuple[OperationAttempt, ...] = ()`, oldest first.
- `TableMaintenanceRun.start_attempt(operation, attempt, job_name, now, *, size: ComputeSize | None = None)`; `succeed(operation, attempt, metrics, now, *, event_log_finished: bool | None = None)` (the entry gets `next_step = done`); `fail(operation, attempt, error, now, *, failure_class: FailureClass = FailureClass.OTHER, event_log_finished: bool | None = None, next_attempt: NextAttempt | None = None)`; `attempt_record(operation, attempt) -> OperationAttempt | None`.
- Output fields: each operation gains `"attempt_history": [{"attempt", "size", "status", "started_at", "finished_at", "failure_class", "error", "event_log_finished", "next_step", "next_size"}, …]` with enum values as strings.

- [ ] **Step 1: Failing tests.**
  - `test_start_attempt_appends_a_running_attempt_with_its_size`; `test_restarting_the_running_attempt_adds_no_entry`.
  - `test_fail_records_class_error_event_log_and_next_step_on_the_attempt`; `test_succeed_marks_the_attempt_done`.
  - `test_three_attempts_keep_three_entries` (S failed `retry_larger` M, M failed `retry_larger` L, L succeeded).
  - `test_finishing_an_attempt_started_before_attempt_history_adds_its_entry` (entry with `size None`, `started_at` from the operation).
  - `test_replayed_outcome_leaves_the_attempt_unchanged` (second `fail` with another class is a no-op, as `_finish` already is).
  - Mapper: `test_attempt_history_round_trips`; `test_row_without_attempt_history_decodes_to_none_recorded`.
  - Output: `test_run_output_lists_every_attempt`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** `OperationRun`'s flat fields (`attempts`, `error`, `metrics`, `job_name`) keep their meaning (the latest attempt), so existing readers and `e2e.sh` are unaffected.
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): keep every attempt of a maintenance operation on its run`.

### Task 4: the table remembers its size and can need attention

**Files:**
- Create in `domain/model/table/`: `applied_policy_ref.py`, `attention_mark.py`; modify `operation_state.py`, `table.py`, package `__init__.py`
- Modify: `adapter/outbound/table/sql/table_row_mapper.py`; `application/service/table/table_output_fields.py`
- Modify: `application/service/table_maintenance_run/create_table_maintenance_run.py`
- Test: `test_operation_state.py`, `test_table.py`, `test_table_row_mapper.py`, `test_create_table_maintenance_run.py`

**Interfaces:**
- `AppliedPolicyRef(ValueObject)`: `name: str`, `version: int`, `target: dict[str, Any] | None` (as `ResolveApplicableTableMaintenancePolicyUseCaseOutput` gives them).
- `AttentionMark(ValueObject)`: `since: datetime`, `reason: str`, `policy: AppliedPolicyRef`.
- `OperationState` gains `last_successful_size: ComputeSize | None = None`, `attention: AttentionMark | None = None`; `start_size() -> ComputeSize` (`last_successful_size` or `S`); `after_success(at, size: ComputeSize | None = None)` (remembers `size` when given, clears `attention`); `with_attention(mark)`; `without_attention()`; `needs_attention_under(policy: AppliedPolicyRef) -> bool`.
- `Table.record_operation_result(op, succeeded, at, *, size: ComputeSize | None = None)`; `Table.mark_needs_attention(op, mark: AttentionMark, at)`; `Table.clear_needs_attention(op, at)` (idempotent; a dropped table refuses all three as today).
- Table output `operation_states[op]` gains `"last_successful_size"` and `"needs_attention"` (`{"since", "reason", "policy_name", "policy_version"}` or `None`).
- `CreateTableMaintenanceRunService`: creating a new run with trigger `manual` clears needs attention of each of its operations on the table (an existing run id changes nothing).

- [ ] **Step 1: Failing tests.**
  - `test_start_size_defaults_to_s`; `test_success_remembers_its_size`; `test_success_without_a_size_keeps_the_remembered_one`.
  - `test_failure_keeps_the_remembered_size`; `test_success_clears_attention`.
  - `test_needs_attention_only_under_the_policy_it_was_marked_under` (same name and version, other target → `False`).
  - Mapper: `test_operation_state_round_trips_size_and_attention`; `test_operation_state_without_new_keys_decodes_with_defaults`.
  - `test_manual_run_clears_needs_attention_of_its_operations` (only the run's operations; a scheduled run clears nothing; re-creating the same run id saves no table).
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): remember each table's last successful size and attention mark`.

### Task 5: reconcile plans from the remembered size and skips what needs attention

**Files:**
- Modify: `domain/model/shared/operation_verdict.py` (`NEEDS_ATTENTION = "needs_attention"`)
- Modify: `domain/service/table/assess_maintenance.py` (new keyword `applied: AppliedPolicyRef | None = None`)
- Modify: `application/port/inbound/table/plan_table_maintenance/output.py` (`PlanTableMaintenanceUseCaseOutputItem.start_size: str = "S"`)
- Modify: `application/service/table/plan_table_maintenance.py` (pass `applied`, `_VERDICTS[NEEDS_ATTENTION] = "needs_attention"`, `start_size` on scheduled and manual items), `get_table_health.py` (pass `applied`)
- Modify: `domain/model/table_reconciliation/operation_result.py` (`NEEDS_ATTENTION = "needs_attention"`) and the verdict map in `service/table_reconciliation/record_table_reconciliation.py`
- Test: `test_assess_maintenance.py`, `test_plan_table_maintenance.py`, `test_get_table_health.py`, `test_record_table_reconciliation.py`

**Interfaces:**
- `assess_maintenance(table, policy, observation, now, *, applied=None)`: an enabled operation whose state `needs_attention_under(applied)` gets verdict `NEEDS_ATTENTION`, no `planned`, measurements kept; a disabled operation stays `DISABLED`. With `applied=None` the mark is ignored.
- Plan output item `start_size` = `table.operation_state(op).start_size().value`, for manual plans too.

- [ ] **Step 1: Failing tests.**
  - `test_needs_attention_blocks_only_its_operation_under_the_same_policy` (mark on `rewrite_data_files`: that one `needs_attention` and unplanned, `expire_snapshots` still due).
  - `test_a_changed_applicable_policy_lifts_needs_attention` (version 2 vs mark under version 1 → `due`).
  - `test_disabled_wins_over_needs_attention`.
  - `test_plan_reports_needs_attention_in_its_checks` (check verdict `"needs_attention"`, no operation planned).
  - `test_plan_starts_each_operation_at_its_remembered_size` (state `M` → item `start_size == "M"`; no state → `"S"`); `test_manual_plan_starts_at_the_remembered_size`.
  - `test_health_shows_needs_attention`.
  - `test_reconciliation_records_needs_attention` (check verdict maps to `OperationResult.NEEDS_ATTENTION`).
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** Build the `AppliedPolicyRef` from the resolve output in both services.
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): skip an operation that needs attention and plan its remembered size`.

### Task 6: sizes are settings and each attempt is submitted at its size

**Files:**
- Create: `bootstrap/configs/spark_size_settings.py` (`SparkSizeSettings(BaseModel)`: `driver_memory: str`, `executor_memory: str`, `executor_instances: int = 1`)
- Modify: `bootstrap/configs/spark_settings.py` (remove `driver_memory`, `executor_memory`, `executor_instances`; add `size_s`, `size_m`, `size_l: SparkSizeSettings` defaulting to the table in Global Constraints; env `GLAC_SPARK__SIZE_S__DRIVER_MEMORY` etc.), `bootstrap/configs/__init__.py`, `bootstrap/container/build_spark_config.py`
- Create: `adapter/outbound/table_maintenance_run/k8s/spark_size_resources.py` (`SparkSizeResources` frozen dataclass, same three fields)
- Modify: `k8s/spark_k8s_config.py` (`sizes: Mapping[str, SparkSizeResources]`, default S / M / L as above; drop the three single fields), `k8s/spark_application_manifest.py`
- Modify: `port/outbound/table_maintenance_run/submit_maintenance_job/input.py` (`size: str = "S"`); `port/inbound/table_maintenance_run/submit_maintenance_operation/input.py` (`size: str = "S"`); `service/table_maintenance_run/submit_maintenance_operation.py`; `adapter/hybrid/temporal/inbound/activities/table_reconciliation_activities.py` (`size=request.get("size", "S")`)
- Modify: chart `values.yaml` (`spark.sizes.{S,M,L}.{driverMemory,executorMemory,executorInstances}`) and `templates/configmap.yaml` (nine `GLAC_SPARK__SIZE_*` keys)
- Test: `test_spark_settings.py` (or `test_app_settings.py`), `test_build_spark_config.py`, `test_spark_application_manifest.py`, `test_submit_maintenance_operation.py`, `test_activities.py`

**Interfaces:**
- Manifest: `spec.driver.memory`, `spec.executor.memory`, `spec.executor.instances` come from `config.sizes[input.size]`; an unknown size raises `ValueError` naming it. `sparkConf` gains `"spark.kubernetes.executor.deleteOnTermination": "false"` (executor pods stay, with their exit status, until the SparkApplication is deleted and the garbage collector removes them through their owner, the driver pod). `spec.driver.template = {"spec": {"containers": [{"name": "spark-kubernetes-driver", "terminationMessagePolicy": "FallbackToLogsOnError"}]}}`, so a driver that dies with an error carries the tail of its log as its termination message.
- The service validates `size` as `ComputeSize` (`ValidationError` otherwise) and passes it to `run.start_attempt(..., size=...)` and the gateway.

- [ ] **Step 1: Failing tests.**
  - `test_sizes_default_to_s_m_l` (the nine values); `test_size_reads_env` (`GLAC_SPARK__SIZE_L__EXECUTOR_MEMORY=3g`).
  - `test_manifest_uses_the_memory_of_the_attempt_size` (parametrised S / M / L); `test_manifest_keeps_one_core` (`cores == 1`, `coreLimit == "1"` for every size); `test_unknown_size_is_refused`.
  - `test_executor_pods_are_kept_after_they_end`; `test_driver_falls_back_to_its_log_for_the_termination_message`.
  - `test_submit_records_the_attempt_size` (run's attempt entry has `size M`, gateway input `size == "M"`); `test_submit_refuses_an_unknown_size`.
  - `test_submit_activity_defaults_the_size_for_old_requests`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** No `kubectl patch configmap` anywhere: values come only from `values.yaml` (see `docs/agents/known-follow-ups.md`).
- [ ] **Step 4: Run tests and checks; `helm template platform/25-lakehouse-control-plane/chart` renders the nine keys; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): run each maintenance attempt at size S, M or L`.

### Task 7: a gateway reads an attempt's failure evidence

**Files:**
- Create: `port/outbound/table_maintenance_run/read_maintenance_job_evidence/{__init__,gateway,input,output,job_container_exit}.py`
- Modify: `tests/architecture/test_outbound_port_structure.py` (`GATEWAY_EXTRA_FILES` gains `"job_container_exit.py"`)
- Create: `adapter/outbound/table_maintenance_run/k8s/list_maintenance_job_pods.py` (the two-selector pod listing, moved out of `read_maintenance_job_pods_k8s_gateway.py`, which then uses it), `k8s/read_maintenance_job_evidence_k8s_gateway.py`
- Modify: `bootstrap/container/gateways.py`, `build_gateways.py`
- Test: `test_read_maintenance_job_evidence_k8s_gateway.py`, existing `test_read_maintenance_job_pods_k8s_gateway.py` stays green; fake `tests/…/fakes/scripted_read_maintenance_job_evidence_gateway.py`

**Interfaces:**
- `ReadMaintenanceJobEvidenceGateway.read(input: ReadMaintenanceJobEvidenceGatewayInput) -> ReadMaintenanceJobEvidenceGatewayOutput`; input `(run_id: str, operation: str, attempt: int)`; output `(execution_id: str | None, error: str | None, containers: tuple[JobContainerExit, ...])`; `JobContainerExit(role: str, reason: str | None, exit_code: int | None, message: str | None)`.
- The adapter takes `CustomObjectsApi`, `CoreV1Api` and `SparkK8sConfig`. `execution_id` = SparkApplication `status.sparkApplicationId`; `error` = `status.applicationState.errorMessage`; a 404 gives both `None`. Each listed pod contributes its Spark container (`spark-kubernetes-driver` / `spark-kubernetes-executor`, else the first container) when `state.terminated` or `last_state.terminated` is set; `role` is the pod's `spark-role` label. Other API errors propagate. RBAC is unchanged (the worker Role already gets SparkApplications and lists pods).

- [ ] **Step 1: Failing tests.**
  - `test_evidence_reads_the_application_id_and_error`; `test_evidence_of_a_deleted_application_is_empty_but_lists_pods`.
  - `test_evidence_lists_terminated_driver_and_executor_containers` (driver `Error` / 1 with a message, executor `OOMKilled` / 137, a running executor left out).
  - `test_evidence_reads_last_state_of_a_restarted_container`.
  - `test_pods_found_by_either_selector_are_listed_once`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): read the failure evidence of a maintenance attempt`.

### Task 8: a gateway reads whether an attempt's event log finished

**Files:**
- Create: `port/outbound/table_maintenance_run/read_maintenance_event_log/{__init__,gateway,input,output}.py`
- Create: `adapter/outbound/table_maintenance_run/s3/__init__.py`, `s3/read_maintenance_event_log_s3_gateway.py`
- Create: `bootstrap/container/build_event_log_filesystem.py`; modify `gateways.py`, `build_gateways.py`
- Test: `test_read_maintenance_event_log_s3_gateway.py` (on `pyarrow.fs.LocalFileSystem` over `tmp_path`), `test_build_event_log_filesystem.py`; fake `scripted_read_maintenance_event_log_gateway.py`

**Interfaces:**
- `ReadMaintenanceEventLogGateway.read(input: ReadMaintenanceEventLogGatewayInput(execution_id: str)) -> ReadMaintenanceEventLogGatewayOutput(finished: bool | None)`.
- `ReadMaintenanceEventLogS3Gateway(filesystem: pyarrow.fs.FileSystem, base: str)`: `<base>/eventlog_v2_<id>/appstatus_<id>` is a file → `True`; else `<base>/eventlog_v2_<id>/appstatus_<id>.inprogress` → `False`; else `None`. An id outside `[A-Za-z0-9-]+` → `None` without a call.
- `build_event_log_filesystem(settings: AppSettings) -> S3FileSystem` from `catalog.s3_endpoint` (scheme from its prefix), `catalog.s3_region`, the catalog S3 keys when set (else pyarrow's AWS chain, which reads the worker's `table-maintenance-s3` Secret env), path-style; `base` is `spark.event_log_dir` without `s3a://` and trailing `/` (`spark-event-logs`). Built lazily, as `LazyK8sApi` defers the Kubernetes client, so the API component never builds it.

Why this mechanism: Spark renames the marker in `SparkContext.stop()`, which our runtime calls before it posts the callback, and a polled `FAILED` means the driver has exited; so at record time the marker is final, and one `HEAD`-style lookup answers it. Consuming `spark-event-log-completions` would need a new consumer, state and correlation by application id, and its event can arrive after the record; a driver that is OOM-killed never sends one, so its absence proves nothing until a timeout. Recording only, no parsing.

- [ ] **Step 1: Failing tests.**
  - `test_finished_marker_reads_true`, `test_in_progress_marker_reads_false`, `test_no_marker_reads_none`, `test_odd_execution_id_reads_none`.
  - `test_filesystem_uses_the_catalog_endpoint_and_region`; `test_event_log_base_drops_scheme_and_slash`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): read whether a maintenance attempt's event log finished`.

### Task 9: recording a result classifies, decides and remembers

**Files:**
- Modify: `port/inbound/table_maintenance_run/record_table_maintenance_operation_result/input.py` (`ended_by: str = "result"`, `still_running: bool = False`, `max_attempts: int = 3`), `output.py` (`failure_class: str | None = None`, `next_step: str | None = None`, `next_size: str | None = None`)
- Modify: `service/table_maintenance_run/record_table_maintenance_operation_result.py` (constructor adds `evidence_gateway`, `event_log_gateway`, `resolve_applicable_policy`)
- Modify: `adapter/hybrid/temporal/inbound/activities/table_maintenance_activities.py` (map the three new request keys with `.get` defaults)
- Modify: `bootstrap/container/build_use_cases.py`
- Test: `test_record_table_maintenance_operation_result.py`, `test_activities.py`, `test_build_use_cases.py`

**Behaviour** of `execute`, replacing today's:
1. A request for an attempt already finished on the run (lower attempt, or `attempt_record` has an outcome) reads nothing and returns that attempt's stored `failure_class`, `next_step`, `next_size` (all `None` when it has no entry).
2. For a success, or a failure ended by `result` / `job_failed`, read the evidence; when it has an `execution_id`, read the event log. Any exception from either is logged as a warning and treated as no evidence.
3. Success: `run.succeed(..., event_log_finished=…)`; `table.record_operation_result(op, True, now, size=<the attempt's size>)`; output `next_step = "done"`.
4. Failure: `FailureEvidence(ended_by, texts = (request.error, evidence.error, driver termination messages), containers)` → `classify_attempt_failure` → `decide_next_attempt(class, <the attempt's size>, attempt, max_attempts, still_running=…)` → `run.fail(...)`; `table.record_operation_result(op, False, now)`; on `needs_attention` also resolve the applicable policy and `table.mark_needs_attention(op, AttentionMark(since=now, reason="out of memory at size L", policy=…), now)`.
5. The run is saved before the table, as today.

- [ ] **Step 1: Failing tests** (with the two scripted gateways and the existing fakes).
  - `test_oom_text_is_classified_and_retried_at_the_next_size` (S, error with `java.lang.OutOfMemoryError` → output `("oom", "retry_larger", "M")`, the run's attempt entry holds them and the raw error).
  - `test_executor_oom_kill_is_read_from_the_job_evidence` (error "no file group was committed", evidence executor `OOMKilled` → `oom`).
  - `test_event_log_state_is_recorded_on_the_attempt` (failure → `False`; success → `True`; no execution id → `None` and the event log gateway is not called).
  - `test_evidence_is_not_read_for_timed_out_cancelled_or_missing_attempts`.
  - `test_unreadable_evidence_still_records_the_attempt` (evidence gateway raises → class from text, `event_log_finished None`, saved).
  - `test_oom_at_l_marks_the_operation_needs_attention_under_the_applicable_policy` (mark's policy = the resolve output).
  - `test_still_running_failure_stops` (`still_running=True` → `next_step "still_running"`).
  - `test_replayed_record_returns_the_stored_decision` (same request twice: equal outputs, gateways and resolve called once, table saved once).
  - `test_success_remembers_the_size_on_the_table`.
  - Activity: `test_record_activity_passes_ending_and_attempt_limit`; `test_record_activity_defaults_keys_of_old_requests`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** Wire the two gateways and `resolve_applicable_policy` in bootstrap.
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): classify and decide each attempt when its result is recorded`.

### Task 10: the maintenance workflow follows the decision

**Files:**
- Create: `adapter/hybrid/temporal/contracts/table_maintenance/attempt_ending.py` (`MaintenanceAttemptEnding(StrEnum)`, the seven endings), `next_step.py` (`MaintenanceNextStep(StrEnum)`, the eight steps), `default_start_size.py` (`DEFAULT_START_SIZE = "S"`); export them
- Modify: `contracts/table_maintenance/operation_result_signal.py` (`ended_by: str = MaintenanceAttemptEnding.RESULT`, `still_running: bool = False`)
- Modify: `adapter/hybrid/temporal/inbound/workflows/table_maintenance_workflow.py`
- Create: `tests/…/adapter/hybrid/temporal/inbound/fixtures/maintenance_failures_before_failure_classes.json`
- Modify: `scripted_maintenance_activities.py` (`record_replies[(operation, attempt)]` overrides the reply), `test_table_maintenance_workflow.py`, `test_wire_names.py`

**Behaviour:**
- `_run_operation` starts at `operation.get("start_size") or DEFAULT_START_SIZE`; each submit request carries `"size"`.
- Every `_failure` names its ending: callback → `result`, polled `FAILED` → `job_failed`, `_timed_out` → `timed_out`, `_missing` → `missing`, acquire failure → `admission_failed`, submit failure → `submit_failed`, cancel → `cancelled`; the unconfirmed-fence outcome sets `still_running=True`.
- `_record` sends `ended_by`, `still_running`, `max_attempts` and returns the activity's reply (`None` when the record failed).
- After a failed attempt: reply `next_step == retry_larger` → the next attempt uses `next_size`; `retry_same` or no `next_step` → same size, as today; any other step → the operation ends now (no backoff, no further attempt) and the run moves on.

- [ ] **Step 1: Capture the fixture first,** with the workflow still unchanged: a run whose three attempts fail by callback, history written with `WorkflowHistory.to_json()` to the fixture path (as milestone 1 did for `maintenance_timeout_before_fencing.json`).
- [ ] **Step 2: Failing tests.**
  - `test_first_attempt_uses_the_plan_start_size` (`start_size "M"` → first submit `size "M"`); `test_plan_without_start_size_submits_size_s`.
  - `test_attempts_follow_the_recorded_size_decision` (replies `retry_larger M`, `retry_larger L` → submits S, M, L).
  - `test_needs_attention_stops_the_operation_without_another_attempt` (start M; replies `retry_larger L`, then `needs_attention` → two submits, the next operation still runs, parent signalled).
  - `test_record_result_without_a_decision_keeps_retrying_at_the_same_size` (old reply shape → three submits at S).
  - `test_record_reaches_the_ending_of_each_failure` (parametrised: callback failure, FAILED state, timeout, missing job, submit error, cancel → the matching `ended_by`; `max_attempts == 3` on every record).
  - `test_unconfirmed_fence_records_still_running`.
  - `test_failed_attempt_is_recorded_before_its_job_is_deleted` (callback failure: the record precedes every `delete_maintenance_job` of that attempt).
  - `test_history_from_before_failure_classes_replays` (the new fixture), and the three milestone 1 fixtures still replay.
  - Wire names: `test_maintenance_attempt_endings` and `test_maintenance_next_steps` pin every value; `test_domain_and_contract_values_agree` asserts `{e.value for e in AttemptEnding} == {e.value for e in MaintenanceAttemptEnding}` and the same for `NextStep`.
- [ ] **Step 3: Run; they fail.**
- [ ] **Step 4: Implement.** No new activity, timer or signal. Update the class docstring.
- [ ] **Step 5: Run tests, `test_temporal_workflow_sandbox.py`, `test_temporal_workflow_determinism.py` and the four checks; pass.**
- [ ] **Step 6: Commit** `feat(table-maintenance): retry an out-of-memory attempt at the next size`.

### Task 11: the Spark runtime reports peak heap use and keeps the OOM line

**Files:**
- Create: `src/data-platform/runtime/spark/peak_heap_percent.py`, `memory_bytes.py`, `error_text.py`
- Modify: `maintenance_runner.py` (`measure: Callable[[], int | None] | None = None`, called on success before `stop`; the error text through `error_text`), `main.py` (passes `lambda: peak_heap_percent(spark)`)
- Modify: `src/data-platform/runtime/spark/Taskfile.yml` (`unit-test` runs `uv run pytest -v` instead of the `TODO://` echo)
- Test: `tests/test_peak_heap_percent.py`, `tests/test_memory_bytes.py`, `tests/test_error_text.py`, `tests/test_maintenance_runner.py`

**Interfaces:**
- `memory_bytes(value: str) -> int`: Spark memory strings (`"768m"`, `"1g"`, `"1536m"`; no suffix means MiB).
- `peak_heap_percent(spark, *, fetch=<urllib JSON GET>) -> int | None`: reads `<sc.uiWebUrl>/api/v1/applications/<sc.applicationId>/allexecutors`; for each entry with `peakMemoryMetrics.JVMHeapMemory`, divides by `spark.driver.memory` (id `"driver"`) or `spark.executor.memory`; returns the largest whole percent, or `None` when the UI is off, the call fails, or no entry has the metric.
- `error_text(exc) -> str`: `f"{type(exc).__name__}: {exc}"` cut to `MAX_ERROR_LENGTH` (4096); when a line holding `OutOfMemoryError` or `exit code 52` was cut away, that line replaces the tail so the result still holds it and stays within 4096.
- On success the metrics gain `"peak_heap_percent"` when measured.

- [ ] **Step 1: Failing tests.**
  - `test_memory_bytes_parses_spark_sizes`.
  - `test_peak_heap_percent_is_the_largest_share_of_driver_and_executors` (driver 384 MiB of `768m` = 50, executor 1152 MiB of `1536m` = 75 → `75`); `test_peak_heap_percent_is_none_without_metrics`; `test_peak_heap_percent_is_none_when_the_ui_cannot_be_read`.
  - `test_success_reports_peak_heap_percent_before_stop` (call order: measure, stop, post); `test_failure_reports_no_peak`; `test_unmeasured_success_reports_no_peak_key`.
  - `test_error_keeps_the_out_of_memory_line_beyond_the_cap`; `test_short_error_is_unchanged`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** The runtime stays dependency-free (urllib, json).
- [ ] **Step 4: Run the runtime tests and its ruff; pass.**
- [ ] **Step 5: Commit** `feat(spark-runtime): report peak heap use and keep the out-of-memory line of an error`.

### Task 12: a table steps down one size when measured use stays low

**Files:**
- Modify: `domain/model/table/operation_state.py` (`low_use_successes: int = 0`; `after_success(at, size=None, peak_heap_percent: int | None = None)`; class constants `LOW_USE_PERCENT = 50`, `LOW_USE_RUNS = 3`), `table.py` (`record_operation_result(..., peak_heap_percent=None)`), the table row mapper
- Modify: `record_table_maintenance_operation_result.py` (passes `metrics.get("peak_heap_percent")`)
- Test: `test_operation_state.py`, `test_table_row_mapper.py`, `test_record_table_maintenance_operation_result.py`

**Behaviour:** a success at the remembered size with `peak_heap_percent < 50` adds one to `low_use_successes`; at 3 the remembered size becomes `size.smaller()` (when there is one) and the count resets. A success at another size, with `peak_heap_percent >= 50`, or with no measurement resets the count to 0 (or to 1 for a low-use success at a new size).

- [ ] **Step 1: Failing tests.**
  - `test_three_low_use_successes_step_down_one_size` (M, 40 / 40 / 40 → `start_size() is S`).
  - `test_a_high_use_success_resets_the_low_use_streak` (40, 60, 40, 40 → still M).
  - `test_an_unmeasured_success_resets_the_low_use_streak`.
  - `test_size_s_never_steps_below_s`.
  - `test_success_at_a_new_size_starts_a_new_streak`.
  - `test_record_passes_the_measured_peak_to_the_table`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): step a table down one size after three low-use runs`.

### Task 13: the run API types its operations and attempts

**Files:**
- Modify: `adapter/inbound/web/table_maintenance_run/dto.py` (`TableMaintenanceRunAttemptApiResponse`, `TableMaintenanceRunOperationApiResponse`; `TableMaintenanceRunApiResponse.operations: list[TableMaintenanceRunOperationApiResponse]`)
- Regenerate: `task dev:generate-api` (`openapi.json`, `src/data-platform/frontend/src/api/generated`)
- Modify: `src/data-platform/frontend/src/components/tabs/MaintenanceTab.tsx` (`OperationDetail` takes `TableMaintenanceRunOperationApiResponse`; no visible change), `src/stories/storyData.ts` (runs carry `attempt_history`)
- Test: the run router tests, the contract test, `MaintenanceTab.test.tsx`

**Interfaces:**
- `TableMaintenanceRunAttemptApiResponse`: `attempt: int`, `size: str | None`, `status: str`, `started_at: datetime`, `finished_at: datetime | None`, `failure_class: str | None`, `error: str | None`, `event_log_finished: bool | None`, `next_step: str | None`, `next_size: str | None`.
- `TableMaintenanceRunOperationApiResponse`: today's keys (`operation`, `status`, `attempts`, `started_at`, `finished_at`, `job_name`, `metrics: dict[str, int]`, `error`, `expected_files`) plus `attempt_history: list[TableMaintenanceRunAttemptApiResponse]`.

- [ ] **Step 1: Failing tests.** `test_run_response_lists_each_attempt` (router: GET a run with two attempts → `operations[0].attempt_history[1].size == "M"`); the contract test fails on the stale `openapi.json`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement, regenerate, adapt the console types.**
- [ ] **Step 4: Backend tests and checks, console unit and story tests; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): type the attempts of a maintenance run in its API`.

### Task 14: the console shows every attempt and needs attention

**Files:**
- Create: `src/data-platform/frontend/src/lib/attemptText.ts`, `attemptText.test.ts`
- Modify: `src/components/tabs/MaintenanceTab.tsx` (an attempts `DataTable` per operation, columns from `createDataTableColumnHelper`), `MaintenanceTab.test.tsx`
- Modify: `src/components/HealthPanel.tsx`, `HealthPanel.test.tsx`; `src/components/tabs/reconciliationText.ts`, `reconciliationText.test.ts`
- Modify: `src/pages/TablePage.stories.tsx`, `src/stories/storyData.ts`

**Interfaces:**
- `failureClassText(c)`: `oom` "Out of memory", `timeout` "Timed out", `commit_conflict` "Conflicted with another commit", `permanent` "Retrying cannot fix it", `cancelled` "Cancelled", `other` "Other error"; `null` "".
- `nextStepText(step, nextSize)`: `done` "Done", `retry_larger` "Retrying at size M" (the size), `retry_same` "Retrying at the same size", `needs_attention` "Stopped: needs attention", `attempts_used` "Stopped: no attempts left", `not_retried` "Stopped: retrying will not help", `cancelled` "Stopped: cancelled", `still_running` "Stopped: its job is still running"; `null` "" (a running attempt).
- `eventLogText(finished)`: `true` "Finished", `false` "Did not finish", `null` "Unknown".
- Attempts table caption `Attempts of <operation>`; columns Attempt, Size, Result (`RunStatusBadge`), Reason, Event log, Next. The raw error stays under the table in `text-negative-text`. A run without `attempt_history` keeps today's attempt count line.
- Health line for verdict `needs_attention`: "Needs attention: out of memory at the largest size. A manual run or a policy change retries it." in `text-negative-text`. Reconciliation label "Needs attention", sentence "Not started: it ran out of memory at the largest size and waits for a manual run or a policy change."

- [ ] **Step 1: Failing tests.**
  - `attemptText.test.ts`: every value above.
  - `lists every attempt with size, result, reason, event log and next step` (attempt 1: S, Failed, Out of memory, Did not finish, Retrying at size M; attempt 2: M, Succeeded, Finished, Done).
  - `keeps the attempt count for runs from before attempt history`.
  - `shows needs attention in the health panel as an error`; reconciliation label and sentence.
  - Story `Pages/Table` `MaintenanceAttemptsEscalated` (the S → M run) and its phone-width variant with `expectNoHorizontalPageScroll`; story `HealthNeedsAttention`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement** from design-system parts only; status colours only for status.
- [ ] **Step 4: Console unit tests and story tests; pass.**
- [ ] **Step 5: Commit** `feat(console): show each attempt's size, failure and next step`.

### Task 15: documentation

**Files:**
- Modify: `platform/25-lakehouse-control-plane/README.md` ("Configuration": the size table and their keys; "Spark event logs": executors are kept until the run ends; how `event_log_finished` is read)
- Modify: `docs/agents/project-history.md` (one line), `docs/agents/known-follow-ups.md` (the risks in Verification step 7 that remain), `platform/CLAUDE.md` (wave 25 line: Spark jobs run at size S / M / L)

- [ ] **Step 1: Write them; `pre-commit run shared --all-files` passes.**
- [ ] **Step 2: Commit** `docs(table-maintenance): record failure classes, sizes and OOM escalation`.

---

## Verification on the cluster (main session, after review)

**Deploy size: small.** Only wave 25 changes (backend and Spark images, chart values and ConfigMap keys); no CRD, no Temporal namespace or search-attribute change, no other wave, no new namespace, no RBAC change, and the workflow change replays existing histories (Task 10). Redeploy with `KUBE_CONTEXT=retail-lakehouse platform/25-lakehouse-control-plane/bootstrap.sh` when no maintenance run is in flight. Then run `KUBE_CONTEXT=retail-lakehouse platform/25-lakehouse-control-plane/e2e.sh` once on that cluster, because every job's default memory shrank from 1g / 1g to S (768m / 768m): the e2e is the regression check that its tables still compact at S (an OOM there would show as an S → M escalation, which the e2e does not assert against, so read the attempt sizes in its run dump). Open the API with `kubectl port-forward service/table-maintenance-api 8000:8000 --namespace lakehouse-control-plane --context retail-lakehouse`.

1. **Sizes on a normal job.** Manual `rewrite_data_files` on `tm_e2e_orders`. `kubectl get pods --namespace lakehouse-maintenance-operations --context retail-lakehouse --selector table-maintenance/run-id=<run> --output custom-columns=NAME:.metadata.name,MEM:.spec.containers[0].resources.requests.memory,POLICY:.spec.containers[0].terminationMessagePolicy` shows about 1152Mi for driver and executor and `FallbackToLogsOnError` on the driver. The run's attempt 1 has size `S`, `event_log_finished: true`, next step `done`, and its metrics hold `peak_heap_percent`. If the measured requests differ from the table in Global Constraints, write the real L cost on KCL-48.
2. **Craft a table that overflows S and fits M.** The executor's Parquet writer keeps a whole row group in heap; one large row group of barely compressible data needs more heap than S has and less than M.
   - Trino: `CREATE TABLE iceberg.e2e.tm_oom_wide (id bigint, c1 varchar, c2 varchar, c3 varchar, c4 varchar)` (unpartitioned), then 24 times `INSERT INTO iceberg.e2e.tm_oom_wide SELECT a.x * 1000 + b.y, to_hex(sha512(to_utf8(CAST(a.x * 1000 + b.y AS varchar) || '1'))), … '2' …, … '3' …, … '4' … FROM UNNEST(sequence(1, 100)) AS a(x) CROSS JOIN UNNEST(sequence(1, 1000)) AS b(y)` (100k rows × 4 × 128 hex characters ≈ 51 MB raw, about 28 MB in zstd Parquet, each insert at least one file): about 1.2 GB raw, about 670 MB on disk, in 24+ files.
   - In the worker pod (`kubectl exec deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse -- python -c …`), with `build_catalog_factory(get_settings().catalog)("iceberg")`, set the table properties `write.parquet.row-group-size-bytes = 1073741824` and `write.target-file-size-bytes = 1073741824`, so the rewrite writes one file and one row group of about 670 MB.
   - Make sure a discovery rule includes `iceberg.e2e.*` (the e2e's rule, or `PUT /v1/discovery-rules`) and `GET /v1/tables` lists the table as managed.
   - Calibrate if needed: S succeeds → add 12 more inserts; M fails too → drop the table and use 16 inserts.
3. **Observe S fail as `oom` and M succeed.** `POST /v1/tables/<uuid>/maintenance '{"operations": ["rewrite_data_files"]}'`. While attempt 1 runs, watch `kubectl get pods … --selector table-maintenance/run-id=<run>,table-maintenance/attempt=1 --output custom-columns=NAME:.metadata.name,ROLE:.metadata.labels.spark-role,REASON:.status.containerStatuses[0].state.terminated.reason,EXIT:.status.containerStatuses[0].state.terminated.exitCode` and note which signal fired (executor exit 52, `OOMKilled`, or the text). Then: attempt 1 `size S`, `failure_class oom`, raw error recorded, `event_log_finished` as recorded matches the marker in `spark-event-logs/eventlog_v2_<appId>/` (list it from the worker pod with pyarrow, `appId` from the run's SparkApplication before it is deleted), next step `retry_larger` M; attempt 2 `size M` succeeded, its pods request about 1434Mi / 2150Mi. The console Maintenance tab shows both attempts with size, result, reason, event log and next step. `GET /v1/tables/<uuid>` shows `last_successful_size: "M"`; a second manual run starts at M.
4. **Force an OOM at L.** Edit `values.yaml` so every size has `driverMemory: 768m` and `executorMemory: 768m`, redeploy wave 25, manual run on `tm_oom_wide`: attempt 1 at M (768m) `oom` → attempt 2 at L (768m) `oom` → next step `needs_attention`, no attempt 3. `GET /v1/tables/<uuid>/health` shows `rewrite_data_files` `needs_attention`; the console's health panel says so. `POST /v1/tables/<uuid>/reconcile`: the reconciliation record shows `needs_attention` for compaction and starts no compaction run.
5. **Clear it.** Attach another policy to the table (`PUT /v1/maintenance-policies/<name>/mappings` with the table target): health no longer shows `needs_attention`. Detach it again. Restore the sizes: `git restore platform/25-lakehouse-control-plane/chart/values.yaml` and redeploy wave 25 (never `kubectl patch configmap`, which makes the next bootstrap fail with a server-side-apply conflict). A manual run then succeeds at M and the table's mark is gone.
6. **Clean up.** `DROP TABLE iceberg.e2e.tm_oom_wide` (its files stay in RustFS, about 700 MB, since deletes do not purge; acceptable on minikube).
7. **Risks to write down** (on the issue named):
   - KCL-51: step-down relies on `peak_heap_percent`. If step 1 shows no such metric, step-down never fires; if JVM used-heap peaks track GC rather than need, it fires late or flaps (at worst one OOM attempt every fourth run). Step-down is covered by unit tests only; three low-use runs were not forced on the cluster.
   - KCL-48: an L job does not fit next to any other Spark job on this node; the second waits Pending while its attempt deadline runs. L's cost is about 5017Mi of requests.
   - KCL-49: a driver JVM that dies of OOM without an error exit, or before it logs, is classified `other`; timed-out, cancelled and missing attempts record `event_log_finished: null` (their SparkApplication is gone before the record).
   - KCL-50: "less work per attempt" waits for milestone 3.

**E2e decision for the main session:** the OOM scenario needs about 1.2 GB of crafted data and three Spark attempts, so it stays out of the e2e. Cheap and worth adding: assert that every attempt in the e2e's run dump has a `size` and that each succeeded attempt has `event_log_finished: true`.
