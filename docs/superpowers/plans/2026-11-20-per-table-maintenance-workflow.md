# Per-Table Maintenance Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From "the reconciliation decided what a table needs" to "Spark runs" there is one per-table maintenance workflow that hands each operation straight to Volcano; compaction rounds, admission and compaction candidates are gone, queue wait is timed apart from run time, and a manual run raises the priority of a run already in flight.

**Architecture:** The reconciliation workflow starts one `TableMaintenanceWorkflow` child per run under the id `table-maintenance:table-uuid={uuid}`, so Temporal allows one per table. The child submits each operation as a SparkApplication into the Volcano queue of the run's priority and waits; an attempt is `queued` until its driver container starts, and only then does its deadline start. A manual trigger on a table whose run is in flight becomes a `raise_priority` signal to that child, which records the new priority on the run and resubmits an attempt still waiting in Volcano.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK, Kubernetes Python client, Helm, Volcano 1.16.0, Spark Operator 2.3.0, React + TanStack Query + orval + MSW.

**Spec:** Linear KCL-93 (https://linear.app/kcl10/issue/KCL-93), the KCL-89 comments of 2026-11-19 (orchestration, priority and queue decisions), and the decisions in the brief that ordered this plan (copied into Global Constraints). The KCL-92 plan `docs/superpowers/plans/2026-11-19-table-priority-volcano-queues.md` is what this builds on.

## Global Constraints

- Remove completely: `CompactionRoundWorkflow` and schedule `compaction-rounds`; `TableMaintenanceAdmissionWorkflow` with its activities and signals; the `CompactionCandidate` and `CompactionRound` aggregates (domain, ports, services, SQL tables, mappers, tests); the APIs `/v1/compaction-rounds`, `/v1/compaction-rounds/{id}`, `/v1/scheduler-settings`, `/v1/tables/{uuid}/compaction-candidates`; the reconciliation `compaction_granted` signal; chart `scheduler.*` and `worker.admissionLimit`; `bootstrap/configs/scheduler_settings.py`; console `CompactionRoundsPage`, `CandidatesTab`, their sidebar entry, routes, stories and tests; the regenerated client for all of these.
- Architecture tests stay green: aggregate list (`tests/architecture/test_aggregates.py`), `AGGREGATE_SQL_PACKAGES`, `test_wire_names.py`, Temporal activity grouping, prefixed ids (`CompactionRoundId` / `CompactionCandidateId` leave `EXPECTED_PREFIXES`; nothing moves to `UNPREFIXED` or `PENDING`).
- `/v1/platform-settings` survives unchanged in path, tag and DTO names; its use case moves to the `table_maintenance_run` aggregate. The Platform settings page loses the scheduler, admission and candidate-selection items.
- One maintenance workflow per table: workflow id `table-maintenance:table-uuid={uuid}`, started by the reconciliation with `start_child_workflow(..., id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE)`; a second start while one runs fails and is recorded as `run_start_failed`. Operations run one Spark job each in the order `rewrite_data_files` → `rewrite_manifests` → `expire_snapshots` → `remove_orphan_files`. Run ids stay `mr-…`.
- `rewrite_data_files` compacts the whole table (no `where`) with the policy's rewrite options. No "fewer partitions after OOM". Size escalation (S/M/L, OOM step-up, remembered size, step-down) and the Spark result callback stay exactly as they are.
- An attempt's deadline (`attempt_deadline_seconds`, 6 h) starts when its driver container starts running, read from the driver pod (`status.containerStatuses[spark-kubernetes-driver].state.running.startedAt`, else `.state.terminated.startedAt`, else `.lastState.terminated.startedAt`). Until then the attempt is `queued`. The attempt records `started_at` (submit, unchanged meaning) and `started_running_at` (driver start, clamped into `[started_at, now]`).
- Queue wait is bounded on its own: `GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS` (default `86400`, chart `worker.queueWaitLimitSeconds: 86400`). An attempt still queued at the limit is fenced and ends `queue_timed_out`, failure class `queue_timeout`, next step `not_retried`.
- A manual run on a table with a run in flight raises that run's priority, only upward (`P0` outranks `P1` outranks `P2` outranks `P3`); equal or lower changes nothing; a manual run with no priority means the table's current priority. The running operation is not interrupted; an attempt still `queued` is deleted and resubmitted under the same attempt number (not counted toward `max_attempts`); later operations use the new priority; the run's `priority` is updated. No new run is started. Changing the table's own priority never touches an in-flight run.
- No data migration and no new `workflow.patched` markers: the cluster is rebuilt before deploy. Patches whose behaviour this plan deletes go with it (`fewer-partitions-after-oom`, `release-unstarted-candidates`, `recheck-held-candidates`, `compaction-granted-signal`, `prefixed-compaction-round-id`); every other existing patch stays as it is.
- Follow `CLAUDE.md`: TDD; one object per file; `from __future__ import annotations`; StrEnum; ABC ports; `uv run`, never bare `python` / `pytest`; never `cd`; kubectl verb first, then flags; never `--no-verify`; never `sops`; never edit `.claude/settings*.json`; do not touch `platform/30-thanos`, `platform/24-e2e-validation`, the ArgoCD path or `.claude/worktrees/`.
- `<pytest>` below means `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`. `<vitest>` means `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run`. Never run two suites at once.
- Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=<backend|frontend|all>`; a commit that changes `openapi.json` regenerates the client with `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`, commits it with the backend change and runs `scope=all`. `git add` names explicit paths. Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- A short job whose result callback arrives before any poll saw the driver running: the attempt still gets `started_running_at` (from the evidence the record reads) and ends `succeeded`, never stuck reading `queued` (Task 3).
- A priority raise that races the driver starting: one attempt never has two live SparkApplications; the resubmit happens only after the old job reads `NOT_FOUND` and has no live pods (Task 7).
- A manual run that arrives while the in-flight run is closing (its workflow is already gone when the reconciliation signals it): the trigger is kept and planned after `maintenance_finished`, not lost (Task 7).
- A late result callback of a table's previous run reaching the reused workflow id: ignored by run id, the current run unaffected (Task 4).
- A driver start time that is before the submit (clock skew) or after `now`: recorded clamped, so queue wait is never negative and the deadline never starts before the submit (Tasks 2 and 6).

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `TM` = `context/table_maintenance`; `TEMPORAL` = `TM/adapter/hybrid/temporal`; tests mirror under `tests/`. Frontend paths are relative to `src/data-platform/frontend/src/`.

| File | Responsibility |
|---|---|
| `TM/application/port/inbound/table_maintenance_run/get_platform_settings/`, `TM/application/service/table_maintenance_run/get_platform_settings.py`, `TM/adapter/inbound/web/table_maintenance_run/platform_settings_router.py` (moved) | platform settings under the run aggregate |
| `TM/application/domain/model/table_maintenance_run/{operation_run_status,run_status,operation_attempt,table_maintenance_run,attempt_ending,failure_class}.py` | `queued`, `started_running_at`, `record_attempt_running`, `raise_priority`, `queue_timed_out` |
| `TM/application/domain/model/shared/table_priority.py` | `outranks` |
| `TM/adapter/outbound/table_maintenance_run/k8s/driver_started_at.py` (new) | driver start time of a pod list |
| `TM/application/port/outbound/table_maintenance_run/read_maintenance_job_pods/output.py`, `read_maintenance_job_evidence/output.py` | `driver_started_at` |
| `TM/application/port/inbound/table_maintenance_run/record_maintenance_attempt_running/` (new), `TM/application/service/table_maintenance_run/record_maintenance_attempt_running.py` (new) | mark an attempt running |
| `TM/application/port/inbound/table_maintenance_run/raise_table_maintenance_run_priority/` (new), `TM/application/service/table_maintenance_run/raise_table_maintenance_run_priority.py` (new) | raise a run's priority |
| `TEMPORAL/contracts/table_maintenance/{activity,signal,attempt_ending,failure_class,workflow_id,workflow_input}.py`, `raise_priority_signal.py` (new), `default_queue_wait_limit_seconds.py` (new) | wire names and inputs |
| `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`, `table_maintenance_attempt_policy.py`, `table_maintenance_fencing_policy.py` | no admission, queue-aware deadline, raise and requeue |
| `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py`, `TEMPORAL/contracts/table_reconciliation/workflow_input.py` | per-table child id, raise routing, no candidates or grants |
| `TM/application/service/table/plan_table_maintenance.py` and its ports | whole-table compaction |
| `bootstrap/configs/app_settings.py`, `bootstrap/container/*` | settings and wiring |
| `platform/25-lakehouse-control-plane/chart/{values.yaml,templates/configmap.yaml}`, `validate.sh`, `e2e.sh`, `README.md` | chart, checks, e2e |
| `components/tabs/MaintenanceTab.tsx`, `lib/attemptText.ts`, `components/RunMaintenanceDialog.tsx` | queued / running in the console |

Deleted wholesale (Tasks 5, 10, 11): `TEMPORAL/contracts/{table_maintenance_admission,compaction_round}/`, `TEMPORAL/inbound/workflows/{table_maintenance_admission_workflow,compaction_round_workflow,compaction_round_activity_policy}.py`, `TEMPORAL/inbound/{ensure_table_maintenance_admission,ensure_compaction_round_schedule}.py`, `TEMPORAL/inbound/activities/compaction_round_activities.py`, every `compaction_candidate/` and `compaction_round/` directory under `TM/` and `tests/context/table_maintenance/`, and on the console `pages/CompactionRoundsPage*`, `components/tabs/CandidatesTab*`, `components/OverdueNote.tsx`, `lib/{candidateText,roundText,useSchedulerPriorities}*`.

---

### Task 1: Move platform settings to the `table_maintenance_run` aggregate

Platform settings reports how runs execute (attempt limits, attempts, Spark sizes, soon the queue wait limit); `table_maintenance_run` is the aggregate that owns that, and it survives this plan.

**Files:**
- Move (`git mv`): `TM/application/port/inbound/compaction_round/get_platform_settings/` → `TM/application/port/inbound/table_maintenance_run/get_platform_settings/`; `TM/application/service/compaction_round/get_platform_settings.py` → `TM/application/service/table_maintenance_run/get_platform_settings.py`; `TM/adapter/inbound/web/compaction_round/platform_settings_router.py` → `TM/adapter/inbound/web/table_maintenance_run/platform_settings_router.py`
- Modify: the three `__init__.py` re-exports on each side; move `PlatformSettingApiResponse`, `PlatformSettingsApiResponse`, `PlatformSettingsGroupApiResponse` from `TM/adapter/inbound/web/compaction_round/dto.py` to `TM/adapter/inbound/web/table_maintenance_run/dto.py`; `TM/adapter/inbound/web/register_routes.py` (import from `table_maintenance_run`); `TM/adapter/inbound/web/shared/web_use_cases.py`; `bootstrap/container/build_use_cases.py`, `use_cases.py`
- Move tests: `tests/.../web/compaction_round/test_platform_settings_route.py` → `tests/.../web/table_maintenance_run/`; `tests/.../service/compaction_round/test_get_platform_settings.py` → `tests/.../service/table_maintenance_run/`

**Interfaces:**
- Produces: `from context.table_maintenance.application.port.inbound.table_maintenance_run import GetPlatformSettingsUseCase, GetPlatformSettingsUseCaseInput, GetPlatformSettingsUseCaseOutput`; `from context.table_maintenance.application.service.table_maintenance_run import GetPlatformSettingsService`. Route, tag, operation id and DTO names unchanged.

- [ ] **Step 1: Move the two test files and change their imports to the new paths.**
- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run/test_platform_settings_route.py tests/context/table_maintenance/application/service/table_maintenance_run/test_get_platform_settings.py -v` → FAIL, import errors.
- [ ] **Step 3: Move the code** with `git mv` and fix every import (`rg -n "compaction_round import \(\n?\s*GetPlatformSettings|platform_settings_router" src/data-platform/backend` finds them).
- [ ] **Step 4: Run them and watch them pass**, then `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` and confirm `git status --short src/data-platform/frontend/src/api openapi.json` shows no change.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `refactor(table-maintenance): file platform settings under the maintenance run aggregate (KCL-93)`.

### Task 2: An attempt is `queued` until it runs

**Files:**
- Modify: `TM/application/domain/model/table_maintenance_run/operation_run_status.py`, `run_status.py`, `operation_attempt.py`, `table_maintenance_run.py`; `TM/adapter/outbound/table_maintenance_run/sql/table_maintenance_run_row_mapper.py` (attempt JSON key `started_running_at`); `TM/application/service/table_maintenance_run/table_maintenance_run_output_fields.py`; the attempt classes in `get_table_maintenance_run/output.py` and `list_table_maintenance_runs/output.py`; `TM/adapter/inbound/web/table_maintenance_run/dto.py` and `router.py`; `openapi.json` + generated client
- Test: `tests/.../domain/model/table_maintenance_run/test_table_maintenance_run.py`, `test_operation_run.py`, `tests/.../outbound/table_maintenance_run/test_table_maintenance_runs_sql_repo.py`, the run router test

**Interfaces:**
- Produces:
  - `OperationRunStatus.QUEUED = "queued"`; `RunStatus.QUEUED = "queued"`.
  - `OperationAttempt.started_running_at: datetime | None = None`, validator: not before `started_at`. `OperationAttempt.finished` is false for `QUEUED` and `RUNNING`.
  - `TableMaintenanceRun.start_attempt(...)` puts the operation and the new attempt in `QUEUED`; repeating it for the current attempt while `QUEUED` or `RUNNING` is a no-op (plus the existing job-name attach).
  - `TableMaintenanceRun.record_attempt_running(operation: MaintenanceOperation, attempt: int, started_running_at: datetime, now: datetime) -> None`: current attempt `QUEUED` → operation and attempt `RUNNING`, attempt `started_running_at = min(max(started_running_at, attempt.started_at), now)`; already `RUNNING` → no-op; finished attempt without `started_running_at` → fills it (clamped to `[started_at, finished_at]`), status unchanged; lower attempt → no-op; never-started attempt → `InvalidRunTransition`.
  - `attach_job_name` accepts `QUEUED` or `RUNNING`; `succeed` / `fail` accept from `QUEUED` or `RUNNING` and take `started_running_at: datetime | None = None`, which fills the attempt's when unset (same clamp).
  - `status`: all pending → `PENDING`; any `RUNNING` → `RUNNING`; else any `QUEUED` → `QUEUED`; else any non-terminal → `RUNNING`; terminal rules unchanged.
  - `TableMaintenanceRunAttemptApiResponse.started_running_at: datetime | None` with docstring "When the attempt's Spark driver started running; null while the attempt waits in its queue."

- [ ] **Step 1: Write the failing tests**

```python
def test_a_submitted_attempt_is_queued(): ...            # start_attempt → op.status QUEUED, attempt QUEUED, run.status QUEUED
def test_record_running_moves_queued_to_running(): ...   # at t → op RUNNING, attempt.started_running_at == t, run RUNNING
def test_record_running_twice_is_a_no_op(): ...
def test_running_before_the_submit_is_clamped(): ...     # started_running_at = started_at - 5 s → == started_at
def test_running_after_now_is_clamped(): ...             # started_running_at = now + 5 s → == now
def test_a_result_fills_a_missing_running_time(): ...    # succeed(..., started_running_at=t) from QUEUED → SUCCEEDED, attempt.started_running_at == t
def test_record_running_on_a_finished_attempt_only_fills_the_time(): ...
def test_record_running_of_a_lower_attempt_is_a_no_op(): ...
def test_record_running_of_an_unstarted_attempt_is_refused(): ...  # InvalidRunTransition
def test_queued_attempt_can_fail_without_running(): ...  # fail from QUEUED → FAILED, started_running_at None
```

SQL repo: round trip keeps `started_running_at`; an attempt JSON without the key reads `None`. Router: `GET /v1/table-maintenance-runs/{id}` shows `"status": "queued"` and `"started_running_at": null` for a fresh attempt.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table_maintenance_run -v` → FAIL, no `QUEUED`.
- [ ] **Step 3: Implement**; fix every existing test that expected `running` right after `start_attempt` (they now expect `queued`). Regenerate the client.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`.
- [ ] **Step 5: Commit** `feat(table-maintenance): record a maintenance attempt as queued until its job runs (KCL-93)`.

### Task 3: Read when the driver started, and record it

**Files:**
- Create: `TM/adapter/outbound/table_maintenance_run/k8s/driver_started_at.py`; `TM/application/port/inbound/table_maintenance_run/record_maintenance_attempt_running/{__init__,input,output,use_case}.py`; `TM/application/service/table_maintenance_run/record_maintenance_attempt_running.py`
- Modify: `read_maintenance_job_pods/output.py` and `read_maintenance_job_pods_k8s_gateway.py`; `read_maintenance_job_evidence/output.py` and `read_maintenance_job_evidence_k8s_gateway.py`; `get_maintenance_job_status/output.py` and `TM/application/service/table_maintenance_run/get_maintenance_job_status.py` (also reads the pods gateway); `record_table_maintenance_operation_result.py` (passes the evidence's driver start to `succeed` / `fail`); `TEMPORAL/contracts/table_maintenance/activity.py`; `TEMPORAL/inbound/activities/table_maintenance_activities.py`; `bootstrap/container/build_use_cases.py`, `use_cases.py`, `activities.py`
- Test: new `tests/.../k8s/test_driver_started_at.py`; `test_read_maintenance_job_pods_k8s_gateway.py`, `test_read_maintenance_job_evidence_k8s_gateway.py`; `tests/.../service/table_maintenance_run/test_table_maintenance_job_services.py`, `test_record_table_maintenance_operation_result.py`, new `test_record_maintenance_attempt_running.py`; `test_wire_names.py`; `tests/.../temporal/inbound/test_activities.py`; `tests/bootstrap/test_worker.py`

**Interfaces:**
- Consumes: Task 2 (`record_attempt_running`, `started_running_at` on `succeed` / `fail`).
- Produces:
  - `driver_started_at(pods: Sequence[V1Pod]) -> str | None`: the ISO-8601 start of the `spark-kubernetes-driver` container of the pod labelled `spark-role=driver`, from `state.running.started_at`, else `state.terminated.started_at`, else `last_state.terminated.started_at`; `None` when no driver pod or no such time.
  - `ReadMaintenanceJobPodsGatewayOutput.driver_started_at: str | None = None`; `ReadMaintenanceJobEvidenceGatewayOutput.driver_started_at: str | None = None`.
  - `GetMaintenanceJobStatusUseCaseOutput.driver_started_at: datetime | None`; `GetMaintenanceJobStatusService(read_gateway, pods_gateway)` reads the pods only when the state is not `NOT_FOUND`; a pods read that raises leaves `driver_started_at` `None` and logs a warning (the state still answers).
  - `RecordMaintenanceAttemptRunningUseCaseInput(run_id: str, operation: str, attempt: int, started_running_at: datetime, now: datetime)`; `RecordMaintenanceAttemptRunningUseCaseOutput(status: str, started_running_at: datetime | None)` (the operation's status and the attempt's recorded time after the call). Unknown run → `NotFoundError`; unknown operation → `ValidationError`.
  - `TableMaintenanceActivity.RECORD_MAINTENANCE_ATTEMPT_RUNNING = "record_maintenance_attempt_running"`, method `TableMaintenanceActivities.record_maintenance_attempt_running(request: dict) -> dict`, constructor kwarg `record_running: RecordMaintenanceAttemptRunningUseCase`.

- [ ] **Step 1: Write the failing tests**

```python
def test_driver_start_from_a_running_container(): ...       # driver pod running since T → T.isoformat()
def test_driver_start_from_a_terminated_container(): ...
def test_executor_pods_do_not_count(): ...                  # only an executor running → None
def test_no_driver_pod_is_none(): ...
def test_job_status_reports_the_driver_start(): ...         # state RUNNING + pods driver_started_at → output.driver_started_at
def test_job_status_of_a_missing_job_reads_no_pods(): ...   # NOT_FOUND → pods gateway not called
def test_job_status_survives_a_failed_pods_read(): ...      # pods raises → state kept, driver_started_at None
def test_record_running_saves_the_attempt(): ...            # queued attempt → output.status "running"
def test_a_result_takes_the_driver_start_from_the_evidence(): ...  # queued attempt, evidence driver_started_at T, succeeded → attempt.started_running_at == T
```

`test_wire_names.py`: the `TableMaintenanceActivity` set gains `"RECORD_MAINTENANCE_ATTEMPT_RUNNING": "record_maintenance_attempt_running"`.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/outbound/table_maintenance_run/k8s tests/context/table_maintenance/application/service/table_maintenance_run -v`
- [ ] **Step 3: Implement**; the evidence gateway reuses `driver_started_at` on the pods it already lists.
- [ ] **Step 4: Run and watch them pass**, including `tests/architecture` (activity grouping, inbound port models and structure); `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.
- [ ] **Step 5: Commit** `feat(table-maintenance): read when an attempt's Spark driver started and record it (KCL-93)`.

### Task 4: The maintenance workflow runs without admission, one per table

**Files:**
- Modify: `TEMPORAL/contracts/table_maintenance/workflow_id.py`, `signal.py`; `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`, `table_maintenance_fencing_policy.py`; `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py` (`_start_run`)
- Test: `tests/.../temporal/inbound/test_table_maintenance_workflow.py`, `test_table_reconciliation_workflow.py`, `tests/.../temporal/contracts/test_workflow_ids.py`, `test_wire_names.py`

**Interfaces:**
- Produces:
  - `table_maintenance_workflow_id(table_uuid: str) -> str` returning `f"table-maintenance:table-uuid={table_uuid}"`.
  - `TableMaintenanceSignal` loses `ADMISSION_GRANTED`. The workflow no longer calls `SIGNAL_ADMISSION_ACQUIRE`, never signals the admission workflow (release, renew) and has no `admission_granted` handler; an attempt goes straight from start to `SUBMIT_MAINTENANCE_OPERATION`.
  - `TableMaintenanceFencingPolicy` loses `renew_interval`; `_fence` keeps delete, pod polling, the confirm bound and the still-running failure.
  - The workflow submits `operation["filters"]` on every attempt and ignores `filter_sets`; `_narrowed` and `_FEWER_PARTITIONS_PATCH` are deleted.
  - The reconciliation starts the child with `id=table_maintenance_workflow_id(self._table_uuid)` and `id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE`; `in_flight_workflow_id` holds that id.

- [ ] **Step 1: Write the failing tests**

```python
def test_workflow_id_names_the_table_uuid():
    assert table_maintenance_workflow_id("0b6c…") == "table-maintenance:table-uuid=0b6c…"

async def test_attempt_submits_without_admission(env): ...        # activity log has no signal_admission_acquire; submit comes right after create
async def test_oom_retry_keeps_the_planned_filters(env): ...       # plan with filter_sets → every submit carries operation["filters"]
async def test_late_result_of_another_run_is_ignored(env): ...     # operation_result with run_id of a previous run → no record for it; own result still completes the run
async def test_child_runs_under_the_table_workflow_id(env): ...    # reconciliation starts child id "table-maintenance:table-uuid=<uuid>"
async def test_second_run_for_the_table_is_refused_while_one_runs(env): ...
    # start a stub workflow under that id first; the reconciliation's plan → record activity got run_start_failed True, run_id None
async def test_next_run_reuses_the_id_after_the_first_closed(env): ...
```

Delete the admission tests of the maintenance workflow (grant, unexpected grant, lease, renew); `test_wire_names.py` drops `ADMISSION_GRANTED` from the signal set.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass**, plus `tests/architecture/test_temporal_workflow_determinism.py` and `test_temporal_workflow_sandbox.py`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.
- [ ] **Step 5: Commit** `feat(table-maintenance): run one maintenance workflow per table, straight into Volcano (KCL-93)`.

### Task 5: Remove the admission workflow

**Files:**
- Delete: `TEMPORAL/contracts/table_maintenance_admission/`, `TEMPORAL/inbound/workflows/table_maintenance_admission_workflow.py`, `TEMPORAL/inbound/ensure_table_maintenance_admission.py`, `bootstrap/container/admission_lease_seconds.py`, and their tests (`test_table_maintenance_admission_workflow.py`, `test_ensure_table_maintenance_admission.py`, `tests/bootstrap/container/test_admission_lease_seconds.py`, plus test helpers only they use, such as `requester_stub_workflow.py` and `scripted_release_activity.py` if nothing else imports them)
- Modify: `TEMPORAL/contracts/table_maintenance/activity.py` (drop `SIGNAL_ADMISSION_ACQUIRE`), `attempt_ending.py` (drop `ADMISSION_FAILED`); `TEMPORAL/inbound/activities/table_maintenance_activities.py` (drop the method and the `admission_limit` / `admission_lease_seconds` kwargs); `TEMPORAL/inbound/workflows/__init__.py`, `TEMPORAL/inbound/__init__.py`; `TM/application/domain/model/table_maintenance_run/attempt_ending.py` (drop `ADMISSION_FAILED`); `bootstrap/configs/app_settings.py` (drop `admission_limit`); `bootstrap/container/{apply_worker_startup,build_activities,build_worker,build_platform_settings,__init__}.py`; `TM/application/domain/model/shared/platform_settings.py` and `get_platform_settings.py` (drop `admission_limit` and its "Concurrent operations" item); `tests/architecture/test_temporal_activity_grouping.py` (drop the `SIGNAL_ADMISSION_ACQUIRE` row of `SIGNAL_EXCEPTIONS`); `test_wire_names.py`, `test_workflow_ids.py`, `test_workflow_summaries.py`, `test_temporal_contracts.py`, `tests/bootstrap/...` tests that name admission
- Modify (chart): `platform/25-lakehouse-control-plane/chart/values.yaml` (drop `worker.admissionLimit`), `chart/templates/configmap.yaml` (drop `GLAC_ADMISSION_LIMIT`), `validate.sh` (replace the admission check)

**Interfaces:**
- Produces: `apply_worker_startup(...)` ensures only the per-catalog discovery schedules and (until Task 11) the compaction round schedule. `validate.sh` asserts `temporal workflow describe --workflow-id table-maintenance-admission` fails with not found, using the same `kubectl exec "${ADMIN_TOOLS}"` form as its other Temporal checks.

- [ ] **Step 1: Update the tests first:** wire names without `SIGNAL_ADMISSION_ACQUIRE` and `ADMISSION_FAILED`; `test_apply_worker_startup.py` asserts no admission ensure is called; `test_app_settings.py` asserts `GLAC_ADMISSION_LIMIT` is no field (`"admission_limit" not in AppSettings.model_fields`); the platform settings test no longer lists `admission_limit`.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal/contracts tests/bootstrap -v`
- [ ] **Step 3: Delete and edit.** Then `rg -n -i "admission" src/data-platform/backend platform/25-lakehouse-control-plane/chart platform/25-lakehouse-control-plane/validate.sh` returns nothing.
- [ ] **Step 4: Run and watch them pass**; `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c GLAC_ADMISSION_LIMIT` → `0`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.
- [ ] **Step 5: Commit** `refactor(table-maintenance): remove the maintenance admission workflow (KCL-93)`.

### Task 6: Queue wait does not count toward an attempt's deadline

**Files:**
- Create: `TEMPORAL/contracts/table_maintenance/default_queue_wait_limit_seconds.py` (`DEFAULT_QUEUE_WAIT_LIMIT_SECONDS = 86400`)
- Modify: `TEMPORAL/contracts/table_maintenance/{workflow_input,attempt_ending,failure_class,__init__}.py`; `TEMPORAL/contracts/table_reconciliation/workflow_input.py`; `TEMPORAL/inbound/workflows/{table_maintenance_workflow,table_maintenance_attempt_policy,table_reconciliation_workflow}.py`; `TEMPORAL/inbound/activities/table_reconciliation_activities.py` (plan output carries `queue_wait_limit_seconds`); `TM/application/domain/model/table_maintenance_run/{attempt_ending,failure_class}.py`; `TM/application/domain/service/table_maintenance_run/{classify_attempt_failure,decide_next_attempt}.py`; `bootstrap/configs/app_settings.py`, `bootstrap/container/{build_activities,build_platform_settings}.py`; `TM/application/domain/model/shared/platform_settings.py`, `TM/application/service/table_maintenance_run/get_platform_settings.py`; chart `values.yaml` (`worker.queueWaitLimitSeconds: 86400`) and `configmap.yaml` (`GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS`)
- Test: `test_table_maintenance_workflow.py`, `test_table_reconciliation_workflow.py`, `tests/.../temporal/inbound/test_table_maintenance_attempt_policy.py` (create if absent), `tests/.../domain/service/table_maintenance_run/` tests of classify and decide, `test_wire_names.py`, `test_app_settings.py`, `test_get_platform_settings.py`

**Interfaces:**
- Consumes: Task 3 (`driver_started_at` in the job status, `RECORD_MAINTENANCE_ATTEMPT_RUNNING`).
- Produces:
  - `AppSettings.maintenance_queue_wait_limit_seconds: int = Field(default=86400, ge=1)`.
  - `TableMaintenanceWorkflowInput.queue_wait_limit_seconds: int = DEFAULT_QUEUE_WAIT_LIMIT_SECONDS`; `TableReconciliationWorkflowInput.in_flight_queue_wait_limit_seconds: int = DEFAULT_QUEUE_WAIT_LIMIT_SECONDS` (carried through continue-as-new, reset by `_clear_in_flight`); the plan activity output key `"queue_wait_limit_seconds"`.
  - `TableMaintenanceAttemptPolicy.queue_wait_limit: timedelta`; `operation_worst_case() = (queue_wait_limit + attempt_deadline + fencing.confirm_bound) × max_attempts + total_backoff()`; `unfenced_operation_worst_case()` unchanged.
  - `AttemptEnding.QUEUE_TIMED_OUT = "queue_timed_out"` and `MaintenanceAttemptEnding.QUEUE_TIMED_OUT`; `FailureClass.QUEUE_TIMEOUT = "queue_timeout"` and `MaintenanceFailureClass.QUEUE_TIMEOUT`; `classify_attempt_failure` maps `QUEUE_TIMED_OUT` → `QUEUE_TIMEOUT`; `decide_next_attempt` maps `QUEUE_TIMEOUT` → `NextStep.NOT_RETRIED` (in `STOPPING_CLASSES`).
  - In `_await_outcome`: `submitted_at = workflow.now()`, `deadline = submitted_at + queue_wait_limit`. Each status poll whose `driver_started_at` is set while the attempt has no `running_since` sets `running_since = min(max(parsed, submitted_at), workflow.now())`, `deadline = running_since + attempt_deadline`, and calls `RECORD_MAINTENANCE_ATTEMPT_RUNNING` (a failed call is logged and the deadline still moves). The fast poll window counts from `running_since or submitted_at`. A deadline reached with no `running_since` fences with reason `"spark job waited in the queue longer than the queue wait limit"`, ending `QUEUE_TIMED_OUT`, `since="the queue wait limit"`; with `running_since` it times out as today.
  - Platform settings: field `queue_wait_limit_seconds: int`; item key `maintenance_queue_wait_limit_seconds`, label `Queue wait limit`, unit `seconds`, description "How long one attempt may wait in its Volcano queue before it is stopped; its operation then waits for the next plan." The `maintenance_attempt_deadline_seconds` description becomes "How long one attempt may run once its Spark job has started; time spent waiting in the queue does not count."

- [ ] **Step 1: Write the failing tests**

```python
async def test_queue_wait_does_not_count_toward_the_deadline(env):
    # deadline 1 h, queue limit 24 h; the status reports no driver start for 3 h, then driver_started_at = T
    # → no timeout at 1 h; the attempt times out at T + 1 h, ending timed_out
async def test_attempt_is_recorded_running_once(env): ...          # record_maintenance_attempt_running called once with started_running_at T
async def test_queued_past_the_limit_ends_queue_timed_out(env): ...  # no driver start for 24 h → job deleted, pods polled, record ended_by queue_timed_out
async def test_driver_start_before_submit_is_clamped(env): ...     # driver_started_at = submit - 10 min → deadline = submit + deadline
async def test_failed_running_record_still_starts_the_deadline(env): ...
async def test_give_up_waits_for_queue_wait_plus_deadline(env): ...  # reconciliation: in-flight bound includes queue_wait_limit_seconds
def test_worst_case_counts_the_queue_wait():
    policy = TableMaintenanceAttemptPolicy(max_attempts=3, attempt_deadline=timedelta(hours=6), queue_wait_limit=timedelta(hours=24))
    assert policy.operation_worst_case() == (timedelta(hours=30, minutes=15)) * 3 + timedelta(seconds=180)
def test_queue_timeout_is_not_retried():
    assert decide_next_attempt(FailureClass.QUEUE_TIMEOUT, ComputeSize.S, 1, 3).step is NextStep.NOT_RETRIED
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal tests/context/table_maintenance/application/domain/service/table_maintenance_run -v`
- [ ] **Step 3: Implement**; the plan activity reads the limit from a new `TableReconciliationActivities` kwarg `queue_wait_limit_seconds`, wired from `settings.maintenance_queue_wait_limit_seconds`.
- [ ] **Step 4: Run and watch them pass**, plus the determinism and sandbox tests; `helm template … | grep GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS` shows `"86400"`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (the platform settings API shape is unchanged, its content is data).
- [ ] **Step 5: Commit** `feat(table-maintenance): time an attempt from its driver start, with its own queue wait limit (KCL-93)`.

### Task 7: A manual run raises the priority of the run in flight

**Files:**
- Create: `TEMPORAL/contracts/table_maintenance/raise_priority_signal.py`; `TM/application/port/inbound/table_maintenance_run/raise_table_maintenance_run_priority/{__init__,input,output,use_case}.py`; `TM/application/service/table_maintenance_run/raise_table_maintenance_run_priority.py`
- Modify: `TM/application/domain/model/shared/table_priority.py`; `TM/application/domain/model/table_maintenance_run/table_maintenance_run.py`; `TEMPORAL/contracts/table_maintenance/{activity,signal,__init__}.py`; `TEMPORAL/inbound/activities/table_maintenance_activities.py`; `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`, `table_reconciliation_workflow.py`; `bootstrap/container/{build_use_cases,use_cases,activities}.py`
- Test: `tests/.../domain/model/shared/test_table_priority.py`, `test_table_maintenance_run.py`, new `tests/.../service/table_maintenance_run/test_raise_table_maintenance_run_priority.py`, `test_table_maintenance_workflow.py`, `test_table_reconciliation_workflow.py`, `test_wire_names.py`, `test_activities.py`

**Interfaces:**
- Consumes: Tasks 2, 3 and 6 (`queued`, `driver_started_at`, `_fence`, `running_since`).
- Produces:
  - `TablePriority.outranks(self, other: TablePriority) -> bool` (`P0.outranks(P1)` is true, `P1.outranks(P1)` false).
  - `TableMaintenanceRun.raise_priority(priority: TablePriority) -> bool`: sets `priority` and returns true only when `priority.outranks(self.priority)` and the run is not finished.
  - `RaiseTableMaintenanceRunPriorityUseCaseInput(run_id: str, priority: str | None, now: datetime)`; `RaiseTableMaintenanceRunPriorityUseCaseOutput(priority: str, raised: bool)`. `priority=None` resolves to the run's table's current priority (a missing table raises nothing). Unknown priority → `ValidationError`; unknown run → `NotFoundError`. The run is saved only when raised.
  - `TableMaintenanceActivity.RAISE_MAINTENANCE_RUN_PRIORITY = "raise_maintenance_run_priority"`; method `raise_table_maintenance_run_priority`, kwarg `raise_priority: RaiseTableMaintenanceRunPriorityUseCase`.
  - `TableMaintenanceSignal.RAISE_PRIORITY = "raise_priority"`; `@dataclass(frozen=True) class RaisePrioritySignal: priority: str | None = None`.
  - Maintenance workflow: the handler appends to `self._raise_requests`. `_apply_raises() -> bool` drains them in order through the activity (a failed call is logged and dropped) and keeps `self._priority` (initially `plan["priority"]`) at the reply's `priority`; it runs before every submit and whenever `_await_outcome` wakes on a request (its `wait_condition` also wakes on `self._raise_requests`). When it raised and the attempt has no `running_since`, `_requeue(name, attempt, operation, size)` first reads the job status: a `driver_started_at` there makes the attempt running (no requeue). Otherwise it deletes the job, polls with the fencing poll interval until the job reads `NOT_FOUND` and has no live pods, then calls `SUBMIT_MAINTENANCE_OPERATION` again with the same attempt; `submitted_at` and the queue deadline are kept. Neither gone within the fencing confirm bound → the attempt fails like an unconfirmed fence (ending `missing`, error `"queued job could not be replaced: …"`, `still_running=True`), polled slowly until gone.
  - Reconciliation workflow: after the give-up check, `if self._in_flight_run_id is not None and self._pending_manual is not None: await self._raise_in_flight()`. It signals `self._in_flight_workflow_id` with `RAISE_PRIORITY` and `RaisePrioritySignal(self._pending_manual_priority)` through `workflow.get_external_workflow_handle`. Delivered → the manual trigger is consumed (logged "raised the priority of run …") and one `manual_run` is taken off the wake reasons (the key is removed at zero). A `FailureError` → logged, the trigger stays pending and is planned after the run reports, as before.

- [ ] **Step 1: Write the failing tests**

```python
def test_p0_outranks_p3(): assert TablePriority.P0.outranks(TablePriority.P3)
def test_equal_does_not_outrank(): assert not TablePriority.P1.outranks(TablePriority.P1)
def test_raise_only_upward(): ...                       # run P2: raise(P3) False, raise(P2) False, raise(P0) True → P0
def test_finished_run_is_not_raised(): ...
def test_service_raises_to_the_tables_priority_when_none_given(): ...  # table P1, run P3 → output ("P1", True), saved
def test_service_refuses_p9(): ...                      # ValidationError
async def test_raise_requeues_a_queued_attempt(env):
    # attempt queued (no driver start); signal raise_priority P0 → delete_maintenance_job, status polled to NOT_FOUND,
    # pods empty, then a second submit_maintenance_operation with attempt 1; the operation's attempts stay 1
async def test_raise_leaves_a_running_attempt_alone(env): ...      # driver_started_at set → no delete, no second submit
async def test_raise_found_running_at_requeue_time_is_not_requeued(env): ...  # status answers driver_started_at on the requeue check
async def test_next_operation_after_a_raise_submits_after_the_record(env): ...  # raise_maintenance_run_priority recorded before the next submit
async def test_lower_raise_changes_nothing(env): ...              # activity replies raised False → no delete
async def test_queued_job_that_cannot_be_replaced_fails_still_running(env): ...
async def test_manual_trigger_in_flight_signals_the_child(env):
    # run in flight; trigger_now {"operations": [...], "priority": "P0"} → child got raise_priority P0,
    # no new plan after maintenance_finished carries manual_operations, wake_reasons lacks manual_run
async def test_manual_trigger_to_a_gone_child_is_planned_after_the_report(env): ...
```

`test_wire_names.py` adds `RAISE_PRIORITY` and `RAISE_MAINTENANCE_RUN_PRIORITY`.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "raise or outrank or manual_trigger" -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass**, then the whole backend suite and the architecture tests; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.
- [ ] **Step 5: Commit** `feat(table-maintenance): a manual run raises the priority of the run in flight (KCL-93)`.

### Task 8: Compaction plans the whole table, without candidates

After this task nothing reads or writes compaction candidates on the run path; rounds still run but find nothing to grant.

**Files:**
- Delete: `TM/application/service/table/compaction_share.py`; `bootstrap/container/compaction_claim_lease.py` and its test; `tests/.../service/table/test_plan_compaction_candidates.py`, `tests/.../service/table_maintenance_run/test_candidates_follow_their_run.py`, `tests/context/table_maintenance/fakes/plan_after_a_round.py`
- Modify: `TM/application/service/table/plan_table_maintenance.py` (drop `candidates_repo`, `runs_repo`, `selection`, `size_memory`, `claim_lease`, `_share_compaction`, `_released_runs`, `_memory_gb`, `_partitions_of`, `_filter_sets`, `_partition_filters`, every `delete_by_table`); `plan_table_maintenance/input.py` (drop `run_id`), `output.py` (drop `candidate_partitions`, `filter_sets`, `next_check_at`, `CandidatePartition`); `submit_maintenance_operation.py` (drop `candidates_repo`, `_start_candidates`); `record_table_maintenance_operation_result.py` (drop `candidates_repo`, `_finish_candidates`); `TEMPORAL/inbound/workflows/table_reconciliation_workflow.py` (plan payload without `run_id`; delete `_release_unstarted`, `_RELEASE_PATCH`, `_next_plan_after`'s recheck and `_RECHECK_PATCH`: the next plan is one interval on); `TEMPORAL/inbound/activities/table_reconciliation_activities.py` and `TEMPORAL/contracts/table_reconciliation/activity.py` (drop `RELEASE_COMPACTION_CANDIDATES`); `bootstrap/container/{build_use_cases,build_connected_use_cases,build_activities,__init__}.py`; `tests/context/table_maintenance/fakes/plan_service_on_fakes.py`; `tests/architecture/test_temporal_activity_grouping.py` if its samples name the removed member
- Test: `tests/.../service/table/test_plan_table_maintenance_service.py`, `test_table_reconciliation_workflow.py`, submit and record service tests, `test_wire_names.py`

**Interfaces:**
- Produces: a planned `rewrite_data_files` has `filters == ()` and `start_size` = the table's remembered start size for compaction; `procedure_args` unchanged. `assess_maintenance` and `build_partition_filters` are untouched (KCL-94 selects partitions again).

- [ ] **Step 1: Write the failing tests**

```python
def test_due_compaction_targets_the_whole_table(): ...       # per-partition policy, 3 qualifying partitions → op.filters == ()
def test_compaction_starts_at_the_remembered_size(): ...     # table remembers M → start_size "M"
def test_plan_output_has_no_candidate_fields():
    assert {"candidate_partitions", "filter_sets", "next_check_at"}.isdisjoint(PlanTableMaintenanceUseCaseOutput.model_fields)
def test_plan_input_has_no_run_id():
    assert "run_id" not in PlanTableMaintenanceUseCaseInput.model_fields
async def test_unstarted_run_releases_nothing(env): ...        # start fails → no release activity is called
async def test_next_plan_is_one_interval_on(env): ...          # plan output with next_check_at → ignored
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/service/table tests/context/table_maintenance/adapter/hybrid/temporal -v`
- [ ] **Step 3: Implement**; delete the candidate tests of the plan, submit and record services.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.
- [ ] **Step 5: Commit** `feat(table-maintenance): compact the whole table without compaction candidates (KCL-93)`.

### Task 9: The console shows queued and running time

**Files:**
- Modify: `components/tabs/MaintenanceTab.tsx`, `lib/attemptText.ts`, `components/RunStatusBadge.tsx` (label for `queued`), `components/RunMaintenanceDialog.tsx`, `stories/storyData.ts` (a queued attempt, a running one with `started_running_at`, a `queue_timeout` failure), and their tests and stories (`MaintenanceTab.test.tsx`, `lib/attemptText.test.ts`, `RunMaintenanceDialog.test.tsx`, `pages/TablePage.stories.tsx`)
- Test: the files above

**Interfaces:**
- Consumes: the generated client of Tasks 2 and 6 (`TableMaintenanceRunAttemptApiResponse.started_running_at`, statuses `queued`, failure class `queue_timeout`).
- Produces:
  - `queueWaitText(attempt: TableMaintenanceRunAttemptApiResponse, now: Date): string` → `formatDuration(started_at, started_running_at ?? finished_at ?? now)`, suffixed `" (waiting)"` while `status === "queued"`.
  - `runTimeText(attempt, now: Date): string` → `"—"` without `started_running_at`, else `formatDuration(started_running_at, finished_at ?? now)`, suffixed `" (running)"` while `status === "running"`.
  - Attempt table columns "Queued" and "Ran" after "Status"; `failureClassText("queue_timeout") === "Waited too long in the queue"`; `RunStatusBadge` shows `Queued` (neutral tone).
  - `RunMaintenanceDialog` reads the table's newest run (`useListTableMaintenanceRuns(tableUuid, { limit: 1 })`); when its status is `pending`, `queued` or `running` it shows a neutral `Banner`: "A maintenance run is already in flight. Running now does not start another run: it raises that run's priority if you pick a higher one, and changes nothing otherwise." The Run button keeps its label.

- [ ] **Step 1: Write the failing tests:** text helpers for a queued, a running, a finished and a never-run attempt; the attempt table shows both columns; the dialog shows the note for a `queued` newest run and not for a `succeeded` one; keyboard: the note does not take focus, Tab still reaches the operations and Run.
- [ ] **Step 2: Run and watch them fail:** `<vitest> MaintenanceTab attemptText RunMaintenanceDialog`
- [ ] **Step 3: Implement** with design-system parts only (`src/data-platform/frontend/CLAUDE.md`); durations in `tabular-nums`.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`.
- [ ] **Step 5: Commit** `feat(console): show how long a maintenance attempt queued and ran (KCL-93)`.

### Task 10: The console drops compaction rounds and candidates

**Files:**
- Delete: `pages/CompactionRoundsPage.tsx`, `.stories.tsx`, `.test.tsx`; `components/tabs/CandidatesTab.tsx`, `.test.tsx`; `components/OverdueNote.tsx`; `lib/candidateText.ts`, `lib/roundText.ts`, `lib/useSchedulerPriorities.ts` and their tests; `priorityWeightsText` in `lib/priorityText.ts`
- Modify: `AppRoutes.tsx` (+ test), `components/AppShell.tsx` (+ test: no "Compaction rounds" item), `pages/TablePage.tsx` (+ test, stories, `TablePage.mobile.test.tsx`: no Candidates tab; `/candidates` falls back like any unknown tab), `components/PriorityText.tsx` and `lib/priorityText.ts` (the bare priority), `components/PolicyEditor.tsx` (+ test), `pages/PoliciesPage.test.tsx`, `pages/PolicyVersionPage.test.tsx`, `components/tabs/reconciliationText.ts` (+ test: drop `all_held`, `all_claimed`, `awaiting_schedule`, `compaction_granted`), `lib/statusTone.ts` (drop `overdue`), `stories/lakehouseHandlers.ts`, `stories/storyData.ts` (drop `CANDIDATES`, `ROUNDS`, scheduler settings; platform settings without the admission item and the `compaction_scheduling` group, with the queue wait limit item), `test/fixtures.ts` (drop `SCHEDULER_SETTINGS`)

**Interfaces:**
- Produces: `priorityText(priority: string): string` returns `priority`. The policy editor's priority hint reads: "Compaction rounds are gone: this priority no longer orders maintenance. A table's own priority (on its Overview tab) does. KCL-91 removes this field." No console file imports `@/api/generated/compaction-rounds` or `@/api/generated/compaction-candidates`.

- [ ] **Step 1: Update the tests first:** AppShell has no "Compaction rounds" link; TablePage has no "Candidates" tab; `priorityText("P2") === "P2"`; reconciliation texts without the shortfall verdicts.
- [ ] **Step 2: Run and watch them fail:** `<vitest> AppShell TablePage priorityText reconciliationText PolicyEditor`
- [ ] **Step 3: Delete and edit**; `rg -n "compaction-rounds|compaction-candidates|SchedulerSettings|useSchedulerPriorities|CandidatesTab|CompactionRounds" /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend/src --glob '!api/generated/**'` returns nothing.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend` (story tests included).
- [ ] **Step 5: Commit** `refactor(console): drop the compaction rounds page and the candidates tab (KCL-93)`.

### Task 11: Remove compaction rounds and compaction candidates from the backend

Both aggregates are dead after Task 8 (nothing creates candidates, so rounds grant nothing). They go in one commit because the round service, the candidates list and their settings depend on each other.

**Files:**
- Delete: `TEMPORAL/contracts/compaction_round/`; `TEMPORAL/inbound/workflows/{compaction_round_workflow,compaction_round_activity_policy}.py`; `TEMPORAL/inbound/ensure_compaction_round_schedule.py`; `TEMPORAL/inbound/activities/compaction_round_activities.py`; every `compaction_candidate/` and `compaction_round/` package under `TM/application/{domain/model,domain/service,port/inbound,port/outbound,service}/`, `TM/adapter/inbound/web/`, `TM/adapter/outbound/`; `TM/application/domain/model/shared/platform_priority.py`; `TM/application/domain/service/shared/size_for_bytes.py` if nothing else uses it; `bootstrap/configs/{scheduler_settings,priority_weight_settings,priority_sla_settings,compaction_settings}.py`; `bootstrap/container/{build_candidate_selection,build_priority_weights,build_priority_sla}.py`; their tests, `tests/context/table_maintenance/fakes/in_memory_compaction_{candidates,rounds}_repo.py`, `tests/context/table_maintenance/application/service/compaction_round/recorded_round.py`
- Modify: `TEMPORAL/contracts/table_reconciliation/signal.py` (drop `COMPACTION_GRANTED`); `table_reconciliation_workflow.py` (drop the handler, `_REASON_COMPACTION_GRANTED`, `_COMPACTION_GRANTED_PATCH` and the plan-failure warning); `TM/application/domain/model/table_reconciliation/{wake_reason,operation_result}.py` (drop `COMPACTION_GRANTED`, `ALL_HELD`, `ALL_CLAIMED`, `AWAITING_SCHEDULE`); `TEMPORAL/contracts/shared/search_attribute.py`, `TEMPORAL/inbound/workflows/table_search_attribute_keys.py` (drop `GRANTED_TABLE_UUIDS`); `TEMPORAL/inbound/workflows/__init__.py`; `TM/application/service/shared/translate_domain_errors.py` (drop `InvalidCandidateTransition`); `TM/adapter/inbound/web/register_routes.py`, `shared/web_use_cases.py`; `TM/adapter/outbound/shared/sql/create_schema.py` (`AGGREGATE_SQL_PACKAGES` without the two); `TM/application/domain/model/shared/{platform_settings,__init__}.py` and `get_platform_settings.py` (drop `round_seconds`, `budget_gb_hours`, `priorities`, `grant_lease_seconds`, `partitions_per_run`, `quiet_seconds`, `max_quiet_wait_seconds`, `min_partition_bytes` and the `compaction_scheduling` group); `bootstrap/configs/{app_settings,__init__}.py` (drop `scheduler`, `compaction`); `bootstrap/container/{apply_worker_startup,build_use_cases,build_connected_use_cases,build_repositories,repositories,use_cases,activities,build_activities,build_worker,build_platform_settings,__init__}.py`; `tests/architecture/test_aggregates.py` (seven aggregates), `tests/architecture/test_prefixed_ids.py` (drop `CompactionRoundId`, `CompactionCandidateId`), `test_wire_names.py`, `test_workflow_ids.py`, `test_workflow_summaries.py`, `test_temporal_contracts.py`, `test_create_schema.py`, `test_add_missing_indexes.py`, `tests/application/service/conftest.py`, `tests/bootstrap/**` that name them; `openapi.json` + generated client
- Modify (platform): chart `values.yaml` (drop `scheduler:` and `compaction:`), `configmap.yaml` (drop every `GLAC_SCHEDULER__*` and `GLAC_COMPACTION__*`); `platform/25-lakehouse-control-plane/validate.sh` (assert `temporal schedule describe --schedule-id compaction-rounds` fails with not found, and `GET /v1/compaction-rounds` answers 404, written like the existing `/v1/policy-templates` check); `platform/21-temporal/bootstrap.sh`, `validate.sh`, `README.md` (four search attributes, no `GrantedTableUuids`)

**Interfaces:**
- Produces: `aggregates("table_maintenance") == {"catalog_discovery", "table", "table_discovery_rules", "table_maintenance_policy", "table_maintenance_policy_attachment", "table_maintenance_run", "table_reconciliation"}`. `apply_worker_startup` ensures only the discovery schedules. `TableSearchAttribute` has `TABLE_UUID`, `TABLE_NAME`, `MAINTENANCE_OPERATIONS`, `MAINTENANCE_TRIGGER`.

- [ ] **Step 1: Update the guard tests first:** the aggregate set above; `EXPECTED_PREFIXES` without `cr` / `cc`; `AGGREGATE_SQL_PACKAGES` without the two packages; wire names without `COMPACTION_GRANTED`, `CompactionRoundActivity`, `COMPACTION_ROUND_*`, `GRANTED_TABLE_UUIDS`; `test_register_routes.py` asserts `/v1/compaction-rounds`, `/v1/scheduler-settings` and `/v1/tables/{table_uuid}/compaction-candidates` are not routes and `/v1/platform-settings` is.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/architecture tests/context/table_maintenance/adapter/hybrid/temporal/contracts tests/context/table_maintenance/adapter/inbound/web/test_register_routes.py -v`
- [ ] **Step 3: Delete and edit**; regenerate the client. Then `rg -n -i "compaction_round|compactionround|compaction_candidate|compactioncandidate|scheduler_settings|GrantedTableUuids|compaction_granted|GLAC_COMPACTION|GLAC_SCHEDULER" /Users/kcl/Projects/retail-lakehouse/src/data-platform /Users/kcl/Projects/retail-lakehouse/platform/21-temporal /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/validate.sh --glob '!**/node_modules/**'` returns nothing.
- [ ] **Step 4: Run and watch them pass**: the whole backend suite, `lint-imports`, `ty check`; `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c "GLAC_SCHEDULER\|GLAC_COMPACTION"` → `0`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`.
- [ ] **Step 5: Commit** `refactor(table-maintenance): remove compaction rounds and compaction candidates (KCL-93)`.

### Task 12: The end-to-end check follows the new flow

**Files:**
- Modify: `platform/25-lakehouse-control-plane/e2e.sh`

**Interfaces:**
- Consumes: the API and workflow ids of Tasks 2, 4, 6 and 11.
- Produces, in `e2e.sh`:
  - `wait_for_quiet_table` and `wait_for_new_run` count `pending`, `queued` and `running` as in flight.
  - `assert_workflows_found_by_table uuid run_id` expects `table-maintenance:table-uuid=${uuid}` among `TableUuid = "${uuid}"` workflows, and that run's `execution_ref` equal to it.
  - `assert_partition_filter` becomes `assert_whole_table_compaction run_id…`: the run's start input has no non-empty `where` for `rewrite_data_files`.
  - `assert_attempts_timed run_json`: every succeeded attempt has `started_running_at` with `started_at <= started_running_at <= finished_at`.
  - Deleted: `assert_no_failed_candidates`, `assert_compaction_granted_by_round`, the round id in `assert_prefixed_ids` (it checks `mr`, `rc`, `dr`, `mp`), and the per-partition "every partition compacted before any orders run" wait becomes "the regions run finished before the orders run starts" (`wait_for_quiet_table`).
- [ ] **Step 1: Edit**; `shellcheck /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` and `bash -n` pass; `rg -n "compaction-rounds|compaction-candidates|GrantedTableUuids|compaction_granted|:run=" /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` returns nothing.
- [ ] **Step 2:** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (its shared part runs the script hooks). The script itself runs in Task 14.
- [ ] **Step 3: Commit** `test(platform): follow the per-table maintenance workflow in the control-plane e2e (KCL-93)`.

### Task 13: Documentation

**Files:**
- Modify: `src/data-platform/backend/CLAUDE.md` (the aggregate list; delete the "Compaction candidates move grant, then claim" paragraph and write one on the per-table workflow: id, queue-aware deadline, raise and requeue; the Temporal contract package list `table_reconciliation`, `table_maintenance`, `table_discovery` plus `shared`, the activity classes `TableReconciliationActivities`, `TableMaintenanceActivities`, `TableDiscoveryActivities`, the signal-wiring exceptions `SIGNAL_PARENT` and `GET_WORKFLOW_RUNNING`; "today platform settings sits under `table_maintenance_run`"; the settings example `GLAC_MAINTENANCE_MAX_ATTEMPTS` instead of `GLAC_ADMISSION_LIMIT`); root `CLAUDE.md` (aggregate list without `CompactionCandidate`, `CompactionRound`); `docs/adr/0005-bounded-contexts-and-context-map.md` (the table maintenance aggregates and the flow); `docs/adr/0011-prefixed-resource-ids.md` (one line: `cr-` and `cc-` retired with their aggregates on 2026-11-20, not to be reused); `platform/25-lakehouse-control-plane/README.md` (delete "Compaction candidates", the scheduler table and the admission row; the workflow table gets `TableMaintenanceWorkflow` `table-maintenance:table-uuid={uuid}`; a "Queue wait and run time" section; `worker.queueWaitLimitSeconds`); `platform/CLAUDE.md` (wave 21: four search attributes; wave 25: an attempt's deadline starts at its driver start, queue wait limit 24 h); `docs/agents/known-follow-ups.md`; `docs/agents/project-history.md`
- In `known-follow-ups.md` remove: the admission-limit entry, the KCL-92 admission-gap entry, "Raising the priority … is KCL-93's", the compaction candidates (milestone 3), "fewer partitions than granted", compaction rounds (milestone 4), the cooldown-recheck entry (`recheck-held-candidates`), `PlatformPriority.priority`, `GET /v1/scheduler-settings` overlap, the `SIGNAL_PARENT`-called-by-the-round entry, the admission flaky test name; in the prefixed-ids entry drop `prefixed-compaction-round-id` and `CompactionCandidate.granted_round_id`; in the give-up entry drop "ignores admission-queue wait time". Add: a changed table priority does not touch an in-flight run (it applies from the next plan); a manual run while a run is in flight drops the operations that run does not contain; a raise can race the driver start, and an attempt whose driver started between the check and the delete is killed and run again under the same attempt; `assess_maintenance` still selects qualifying partitions that the plan ignores until KCL-94.
- [ ] **Step 1: Edit.** `rg -n -i "admission|compaction round|compaction candidate|CompactionRound|CompactionCandidate|scheduler-settings" /Users/kcl/Projects/retail-lakehouse/CLAUDE.md /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend/CLAUDE.md /Users/kcl/Projects/retail-lakehouse/platform/CLAUDE.md /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/README.md` returns only historical mentions that say they are gone.
- [ ] **Step 2: Add the `project-history.md` line** (2026-11-20, KCL-93: per-table maintenance workflow, rounds / admission / candidates removed, queue wait timed apart, manual raise).
- [ ] **Step 3:** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `docs: record the per-table maintenance workflow (KCL-93)`.

### Task 14: Verify on a rebuilt cluster (controller)

The KCL-92 test tables are gone after a rebuild; create what each check needs. Trino is paused; it comes back only for creating tables and for the e2e, and is scaled to 0 for the queueing checks so two L jobs fit on the node.

- [ ] **Step 1: Rebuild.** `task -d /Users/kcl/Projects/retail-lakehouse --yes offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse --yes onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts`; `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/validate.sh` exits 0 (no admission workflow, no `compaction-rounds` schedule, `/v1/compaction-rounds` 404).
- [ ] **Step 2: Test tables.** `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/23-trino/bootstrap.sh`; create `iceberg.kcl93.a`, `b`, `c` with 20 single-row `INSERT`s each (the `trino_sql` way `e2e.sh` does); add a discovery rule `include iceberg / kcl93 / *` and a policy `kcl93` (rewrite_data_files at ≥ 2 reducible files, reconcile interval 300 s) attached to namespace `iceberg.kcl93`, with the same API calls `e2e.sh`'s `ensure_policy` / `attach_policy` make; set `b` to `P1` (`PUT /v1/tables/{uuid}/priority`). Then `kubectl scale deployment --all --replicas 0 --namespace lakehouse-query-engine --context retail-lakehouse`.
- [ ] **Step 3: Several tables due at once queue by priority.** Trigger P3 manual runs on `a` and `c` and wait for one PodGroup to be `Running`; then trigger `b` (P1, no priority in the request). `kubectl get podgroups --namespace lakehouse-maintenance-operations --context retail-lakehouse --output wide` shows the running one and the others `Pending`/`Inqueue`; when it ends, `b`'s job runs before the remaining P3 one. The waiting runs read `queued` in the API and the console.
- [ ] **Step 4: One table never runs two maintenances.** While `a` has a run in flight, `temporal workflow list --query 'TableUuid = "<a uuid>" AND ExecutionStatus = "Running"'` (in `deployment/temporal-admintools`) lists exactly one `table-maintenance:table-uuid=<a uuid>`; a `reconcile-now` on `a` starts no second one.
- [ ] **Step 5: A P0 manual run resubmits a waiting P3 run.** With one P3 job running in `table-maintenance`, start a P3 run on another table so its attempt waits; trigger a manual `P0` run on that table. Its run's `priority` becomes `P0`, its attempt keeps number 1, its new PodGroup sits in `table-maintenance-urgent` with class `table-maintenance-p0` and runs at once; no second run row appears for that table.
- [ ] **Step 6: Queue wait does not trip the timeout.** Temporarily set `worker.attemptDeadlineSeconds: 120` in the chart's `values.yaml` (not committed) and rerun `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/bootstrap.sh` (never `kubectl patch configmap`, per known-follow-ups); make an attempt wait more than 120 s behind a running job; it ends `succeeded` (its run takes under 120 s once started) and its `started_running_at - started_at` is over 120 s. Restore `values.yaml` with `git -C /Users/kcl/Projects/retail-lakehouse checkout -- platform/25-lakehouse-control-plane/chart/values.yaml` and rerun `bootstrap.sh`.
- [ ] **Step 7: e2e.** `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/23-trino/bootstrap.sh`, then `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` exits 0; scale Trino back to 0 as in Step 2.
- [ ] **Step 8:** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`; record the results on KCL-93 in a dated comment (`docs/agents/linear-issues.md`); push only when the user asks.
