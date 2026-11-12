# Milestone 1: timeout fencing and table search attributes — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task (you are the milestone implementer; do not dispatch subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a timed-out maintenance attempt deletes its SparkApplication and waits until its pods are gone before the admission slot is released and before the next attempt is submitted; every workflow acting on one table can be found in the Temporal UI by table uuid.

**Architecture:** a new outbound port reads the live pods of one attempt by label; the maintenance workflow fences a timed-out attempt (delete, poll pods, renew the admission lease while it waits) before its existing release / backoff / retry. The attempt deadline becomes a worker setting carried to the workflows through the plan activity. Four custom search attributes are registered by the Temporal wave and set by the reconciliation and maintenance workflows; the console's Maintenance tab links to the Temporal UI query.

**Tech stack:** Python 3.14, temporalio, kubernetes client, FastAPI wiring in `bootstrap/`, React console (Vitest, Storybook), Helm, bash.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` (sections "1. Timeout gap" and "Finding a table's workflows in the Temporal UI"). Linear issues KCL-46, KCL-47.

## Global Constraints

- Project rules in `CLAUDE.md` and `src/data-platform/backend/CLAUDE.md` hold: one object per file, descriptive file names, `__init__.py` re-exports, `from __future__ import annotations`, ABC ports, StrEnum, port naming `{Verb}{Noun}Gateway` with verbs from the approved list, no infrastructure words in `application/`, hybrid contracts import only stdlib / base / ports.
- Production attempt deadline stays 6 h (`DEFAULT_ATTEMPT_DEADLINE_SECONDS = 6 * 3600`); the admission lease stays deadline + 15 min.
- Admission limit stays 2 and spans every attempt.
- Search attribute names and types, verbatim: `TableUuid` Keyword, `TableName` Keyword, `MaintenanceOperations` KeywordList, `MaintenanceTrigger` Keyword; Temporal namespace `default`.
- Temporal UI query: `TableUuid = "<uuid>" AND ExecutionStatus = "Running"`.
- A new workflow command on a code path that a history already running on the cluster can reach is guarded with `workflow.patched("<id>")`, so a redeploy does not break running workflows.
- Test commands: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest <path> -v`; before each commit also `ty check`, `ruff check .`, `lint-imports` in the same way. Console: `npm --prefix src/data-platform/frontend run test -- <file>`.
- Post a comment on KCL-46 or KCL-47 (Traditional Chinese, plain words) when a task lands, when you decide something this plan leaves open, and when you are blocked.

## Review Focus

1. **Pods still Terminating after delete** — a pod with a deletion timestamp whose phase is still Running counts as alive; the slot stays held. Test in Task 1.
2. **Pods never disappear** — after the confirm bound the operation fails with a reason that says the pods are still running, no further attempt is submitted, the lease keeps being renewed, and the slot is released only once they are gone. Test in Task 3.
3. **A running workflow replayed by the new worker** — histories started before the deploy must replay without non-determinism. Test in Task 3 (replay an old history) and Task 4.
4. **The job finishes during fencing** — a job that completes between the deadline and the delete is still treated as timed out (the table decides later, per the spec's correctness rule); no double count. Test in Task 3.
5. **Search attributes not registered** — starting a workflow with an unregistered attribute fails; the Temporal wave must register them before wave 25 starts any. `platform/21-temporal/validate.sh` asserts all four exist. Task 5.

---

### Task 1: Spark pods carry the attempt labels, and a port reads an attempt's live pods

**Files:**
- Modify: `context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/spark_application_manifest.py` (driver and executor `labels`)
- Create: `context/table_maintenance/application/port/outbound/table_maintenance_run/read_maintenance_job_pods/{__init__,gateway,input,output}.py`
- Create: `context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/read_maintenance_job_pods_k8s_gateway.py`
- Create: inbound port `application/port/inbound/table_maintenance_run/get_maintenance_job_pods/{__init__,use_case,input,output}.py` and service `application/service/table_maintenance_run/get_maintenance_job_pods.py`, mirroring `get_maintenance_job_status`
- Modify: `adapter/hybrid/temporal/contracts/table_maintenance/activity.py`, `adapter/hybrid/temporal/inbound/activities/table_reconciliation_activities.py`
- Modify: `bootstrap/container/` (`build_k8s_api.py` sibling for the core API, `lazy_k8s_api.py`, `gateways.py`, `build_gateways.py`, `use_cases.py`, `build_use_cases.py`, `build_activities.py`)
- Modify: `platform/25-lakehouse-control-plane/chart/templates/rbac.yaml` (worker Role)
- Test: matching files under `tests/context/table_maintenance/...`, a fake `tests/context/table_maintenance/fakes/scripted_read_maintenance_job_pods_gateway.py`, and `test_wire_names.py`

All backend paths are under `src/data-platform/backend/`.

**Interfaces:**
- Produces: `ReadMaintenanceJobPodsGateway.read(input: ReadMaintenanceJobPodsGatewayInput) -> ReadMaintenanceJobPodsGatewayOutput`; `ReadMaintenanceJobPodsGatewayInput(run_id: str, operation: str, attempt: int)`; `ReadMaintenanceJobPodsGatewayOutput(live_pods: tuple[str, ...])`.
- Produces: activity `TableMaintenanceActivity.GET_MAINTENANCE_JOB_PODS = "get_maintenance_job_pods"`, request `{"run_id", "operation", "attempt"}`, response `{"live_pods": [str, ...]}`, implemented by `TableReconciliationActivities.get_maintenance_job_pods`.

- [ ] **Step 1: Failing tests.**
  - `test_spark_application_labels_driver_and_executor_pods_with_the_attempt`: rendered manifest's `spec.driver.labels` and `spec.executor.labels` each equal `{"table-maintenance/run-id": run_id, "table-maintenance/operation": operation, "table-maintenance/attempt": str(attempt)}`.
  - `test_read_pods_selects_the_attempt_by_label`: a stub core API records `list_namespaced_pod(namespace="lakehouse-maintenance-operations", label_selector="table-maintenance/run-id=r1,table-maintenance/operation=rewrite_data_files,table-maintenance/attempt=2")`.
  - `test_read_pods_counts_pending_running_and_unknown_as_live`: pods in phases `Pending`, `Running`, `Unknown`, `Succeeded`, `Failed` → `live_pods` holds the first three names.
  - `test_read_pods_counts_a_terminating_running_pod_as_live`: phase `Running` with `deletion_timestamp` set → live.
  - `test_get_maintenance_job_pods_activity_returns_live_pod_names` on the activity class with the fake gateway.
  - `test_table_maintenance_activities` in `test_wire_names.py` gains `GET_MAINTENANCE_JOB_PODS == "get_maintenance_job_pods"`.
- [ ] **Step 2: Run them; they fail** (missing labels, missing modules, missing enum member).
- [ ] **Step 3: Implement.** The k8s adapter takes a `CoreV1Api` and the `SparkK8sConfig` (for `namespace`). Bootstrap builds the core API lazily the same way as the custom objects API (widen `LazyK8sApi` to any API object, or add a sibling; one object per file). The worker Role gains `apiGroups: [""]`, `resources: ["pods"]`, `verbs: ["get", "list"]`. An API error other than 404 propagates (the activity retries); there is no 404 case for a list.
- [ ] **Step 4: Run the tests and all four checks; they pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): read the live pods of one maintenance attempt`.

### Task 2: the attempt deadline is a worker setting

**Files:**
- Modify: `bootstrap/configs/app_settings.py` (`maintenance_attempt_deadline_seconds: int = 21600`, env `GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS`)
- Replace: `bootstrap/container/admission_lease_seconds.py` constant with `admission_lease_seconds(settings: AppSettings) -> int` (deadline + 900); update `apply_worker_startup.py`, `build_activities.py`, `bootstrap/container/__init__.py`
- Modify: `TableReconciliationActivities` (constructor takes `attempt_deadline_seconds: int`; `plan_table_maintenance` adds `"attempt_deadline_seconds"` to the plan it returns)
- Modify: `adapter/hybrid/temporal/inbound/workflows/table_reconciliation_workflow.py` (pass the plan's deadline into `TableMaintenanceWorkflowInput.attempt_deadline_seconds`, default `DEFAULT_ATTEMPT_DEADLINE_SECONDS` when the key is missing; the in-flight bound uses `TableMaintenanceAttemptPolicy(attempt_deadline=<that deadline>).operation_worst_case()` plus 1 h; Task 3 adds its fencing bound to it)
- Modify: chart `values.yaml` (`worker.attemptDeadlineSeconds: 21600`) and `templates/configmap.yaml` (`GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS`)
- Test: `tests/bootstrap/...` settings and lease tests, `test_table_reconciliation_activities`, `test_table_reconciliation_workflow.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: plan key `attempt_deadline_seconds: int`; `admission_lease_seconds(settings) -> int`.

- [ ] **Step 1: Failing tests.**
  - `test_attempt_deadline_defaults_to_six_hours` (`AppSettings().maintenance_attempt_deadline_seconds == 21600`) and `test_attempt_deadline_reads_env` (`GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS=120` → `120`).
  - `test_admission_lease_is_deadline_plus_fifteen_minutes` (`120` → `1020`).
  - `test_plan_carries_the_attempt_deadline` on the activity built with `attempt_deadline_seconds=120`.
  - `test_reconciliation_passes_the_plan_deadline_to_the_run`: a plan with `attempt_deadline_seconds=120` → the started child's input has `attempt_deadline_seconds == 120`.
  - `test_reconciliation_defaults_the_deadline_for_old_plans`: a plan without the key → `21600`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement** as listed above.
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): make the maintenance attempt deadline a worker setting`.

### Task 3: fence a timed-out attempt before release and retry

**Files:**
- Create: `adapter/hybrid/temporal/contracts/table_maintenance_admission/renew_signal.py` (`AdmissionRenewSignal(request_id: str)`); modify that package's `signal.py` (`RENEW = "renew"`) and `__init__.py`
- Modify: `adapter/hybrid/temporal/inbound/workflows/table_maintenance_admission_workflow.py` (`renew` handler)
- Modify: `adapter/hybrid/temporal/inbound/workflows/table_maintenance_workflow.py` (fencing)
- Create, if the constants need a home: `adapter/hybrid/temporal/inbound/workflows/table_maintenance_fencing_policy.py` (`FENCE_POLL_INTERVAL = 30 s`, `FENCE_RENEW_INTERVAL = 5 min`, `FENCE_CONFIRM_BOUND = 15 min`, `FENCE_SLOW_POLL_INTERVAL = 5 min`)
- Test: `test_table_maintenance_admission_workflow.py`, `test_table_maintenance_workflow.py`, `test_wire_names.py`

**Interfaces:**
- Consumes: activity `GET_MAINTENANCE_JOB_PODS` (Task 1); the existing `DELETE_MAINTENANCE_JOB` activity.
- Produces: signal `TableMaintenanceAdmissionSignal.RENEW = "renew"` with `AdmissionRenewSignal(request_id)`: a held request's `granted_at` becomes now; an unknown id is ignored. `FENCE_CONFIRM_BOUND`, which this task also adds to the reconciliation workflow's in-flight bound from Task 2 (test: `test_in_flight_bound_includes_the_fencing_bound`).

Behaviour on attempt deadline, replacing the immediate `"spark job timed out"` failure in `_await_outcome`:

1. Run `DELETE_MAINTENANCE_JOB` for the attempt.
2. Poll `GET_MAINTENANCE_JOB_PODS` every `FENCE_POLL_INTERVAL`; signal `RENEW` to the admission workflow every `FENCE_RENEW_INTERVAL` while polling.
3. Pods gone within `FENCE_CONFIRM_BOUND`: the attempt fails with `"spark job timed out"`; the existing release, backoff and retry follow.
4. Pods still live at `FENCE_CONFIRM_BOUND`: the operation's result is recorded as failed with error `"spark job timed out; its pods were still running 15 minutes after deletion"`, no further attempt is made, polling continues every `FENCE_SLOW_POLL_INTERVAL` with renewals until the pods are gone, then the slot is released and the run moves to its next operation.

The fencing path is new code reachable by histories already running at deploy time: guard it with `workflow.patched("fence-timed-out-attempt")`; the unpatched branch keeps today's behaviour.

- [ ] **Step 1: Failing tests** (Temporal time-skipping environment, mocked activities, as the existing workflow tests do).
  - Admission: `test_renew_restarts_the_lease_of_a_holder` (granted at t0, renewed at t0 + lease − 1 min, still held at t0 + lease + 1 min); `test_renew_of_an_unknown_request_is_ignored`.
  - Wire names: `RENEW == "renew"`.
  - Maintenance: `test_timed_out_attempt_deletes_the_job_before_release` (activity call order: delete, pods, …, then the release signal, then the next submit).
  - `test_next_attempt_is_not_submitted_while_pods_are_live` (pods live for three polls, then gone: the second submit happens after the third poll).
  - `test_fencing_renews_the_admission_lease_while_waiting` (pods live for 12 minutes: at least two `renew` signals).
  - `test_unconfirmed_deletion_fails_the_operation_and_keeps_the_slot` (pods live for 20 minutes: result recorded failed with the exact error above at ~15 minutes, no second submit, release only after the pods are gone).
  - `test_job_completing_during_fencing_still_counts_as_timed_out` (status COMPLETED after the deadline but before delete: attempt is still a timeout; no success recorded for that attempt).
  - `test_history_from_before_fencing_replays` (a history recorded with the pre-change workflow on the timeout path replays without non-determinism; use `Replayer` with a history captured in the test from the unpatched path).
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** Keep `_run_attempt`'s `finally` as the single release point; fencing runs inside the attempt, before it. `_finish`'s cleanup of started attempts stays.
- [ ] **Step 4: Run tests, `test_temporal_workflow_sandbox.py`, `test_temporal_workflow_determinism.py` and the four checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): fence a timed-out attempt before its slot is released`.

### Task 4: workflows carry table search attributes

**Files:**
- Create: `adapter/hybrid/temporal/contracts/shared/search_attribute.py` (`TableSearchAttribute(StrEnum)`: `TABLE_UUID = "TableUuid"`, `TABLE_NAME = "TableName"`, `MAINTENANCE_OPERATIONS = "MaintenanceOperations"`, `MAINTENANCE_TRIGGER = "MaintenanceTrigger"`); export from `contracts/shared/__init__.py`. Names only; the `SearchAttributeKey` objects are built where temporalio may be imported.
- Modify: `table_reconciliation_workflow.py` (upsert `TableUuid` at the start of `run`, and `TableName` when a plan names the table, both under `workflow.patched("table-search-attributes")`; the child start in `_start_run` passes `search_attributes` with all four)
- Modify: `adapter/hybrid/temporal/outbound/table/send_table_change_temporal_gateway.py` (start the reconciliation workflow with `TableUuid` and `TableName`)
- Test: `test_wire_names.py`, `test_table_reconciliation_workflow.py`, `test_send_table_change_temporal_gateway.py`

**Interfaces:**
- Produces: `TableSearchAttribute` names; the four attribute values on every reconciliation and maintenance workflow.

- [ ] **Step 1: Failing tests.**
  - `test_table_search_attribute_names`: the four values above, verbatim.
  - `test_maintenance_run_carries_table_search_attributes`: the child start has `TableUuid = table_uuid`, `TableName = plan["table_name"]`, `MaintenanceOperations = [op["operation"] for op in plan["operations"]]`, `MaintenanceTrigger = "scheduled"` (and `"manual"` for a manual run).
  - `test_reconciliation_upserts_its_table_uuid` (the test environment's server must have the attributes registered; register them in the fixture).
  - `test_send_table_change_starts_reconciliation_with_table_search_attributes`.
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement.** Static summaries already read `table name · operations` (maintenance) and the table name (reconciliation); keep them.
- [ ] **Step 4: Run tests and checks; pass.**
- [ ] **Step 5: Commit** `feat(table-maintenance): tag table workflows with search attributes`.

### Task 5: the Temporal wave registers the search attributes

**Files:**
- Modify: `platform/21-temporal/bootstrap.sh` (after the Helm install: wait for `deployment/temporal-admintools` and `temporal-frontend`, then create each missing attribute with `kubectl exec deployment/temporal-admintools --namespace temporal --context "${KUBE_CONTEXT}" -- temporal operator search-attribute create --namespace default --name <name> --type <type>`; skip names `temporal operator search-attribute list --namespace default` already shows, so a re-run is a no-op)
- Modify: `platform/21-temporal/validate.sh` (assert all four exist with their types)
- Modify: `platform/21-temporal/README.md` (one line naming the attributes and why)

- [ ] **Step 1:** Run `KUBE_CONTEXT=retail-lakehouse platform/21-temporal/validate.sh` with the new assertions; it fails (attributes missing).
- [ ] **Step 2:** Run `KUBE_CONTEXT=retail-lakehouse platform/21-temporal/bootstrap.sh`; then validate passes. Run bootstrap a second time; it exits 0 and creates nothing.
- [ ] **Step 3: Commit** `feat(temporal): register the table search attributes`.

This task touches the running cluster's Temporal; it is the one cluster step the implementer runs, because Task 4's code cannot start workflows without it.

### Task 6: the console links a table to its running workflows

**Files:**
- Create: `src/data-platform/frontend/src/lib/temporalWorkflowsUrl.ts` and `temporalWorkflowsUrl.test.ts`
- Modify: the Maintenance tab component (`MaintenanceTab`, reached from `src/pages/TablePage.tsx`) to show a text link "Running workflows in Temporal"
- Modify: `src/pages/TablePage.test.tsx`, `src/pages/TablePage.stories.tsx`

**Interfaces:**
- Produces: `temporalWorkflowsUrl(tableUuid: string): string`.

- [ ] **Step 1: Failing tests.**
  - `temporalWorkflowsUrl("1f0e…")` equals `"/temporal/namespaces/default/workflows?query=" + encodeURIComponent('TableUuid = "1f0e…" AND ExecutionStatus = "Running"')`.
  - The Maintenance tab of a managed table renders a link with that `href` and accessible name "Running workflows in Temporal".
- [ ] **Step 2: Run; they fail.**
- [ ] **Step 3: Implement** with the design system's `TextLink` (a plain anchor child, since the Temporal UI is another app on the same gateway). The link uses the maintenance record's uuid, the one the workflows carry.
- [ ] **Step 4: Run the console unit tests and story tests; pass.**
- [ ] **Step 5: Commit** `feat(console): link a table to its running workflows in Temporal`.

---

## Verification on the cluster (main session, after review)

Size: **large** (Task 5 changes the Temporal wave). After the e2e passes on the rebuilt cluster:

1. **Measure a normal job.** Trigger a manual compaction on `tm-e2e` orders and note how long its SparkApplication runs from submit to completion.
2. **Force a timeout.** Set `worker.attemptDeadlineSeconds` to a value below that duration (start at 120) and redeploy wave 25. Trigger a manual compaction.
3. **Observe**, watching the cluster throughout:
   - Temporal history of the maintenance run: `delete_maintenance_job`, then `get_maintenance_job_pods` until empty, then the admission `release`, then the backoff timer, then the next `submit_maintenance_operation`.
   - `kubectl get pods --namespace lakehouse-maintenance-operations --context retail-lakehouse --selector table-maintenance/run-id=<run>` shows no live pod of attempt N when attempt N+1's SparkApplication is created (compare timestamps).
   - The admission workflow's `state` query never shows more than 2 holders.
4. **Search attributes.** In the Temporal UI (`/temporal`), `TableUuid = "<uuid>" AND ExecutionStatus = "Running"` lists that table's reconciliation workflow and the running maintenance run; the console's Maintenance tab link opens the same query.
5. **Restore** `worker.attemptDeadlineSeconds` to 21600 and redeploy wave 25.
6. **Risk to write down:** the unconfirmed-deletion path (pods that never go away) is covered by workflow tests only; forcing a kubelet that cannot kill a container is not practical on minikube.

E2e decision for the main session: the timeout itself needs a cluster-wide deadline change and stays out of the e2e; a search-attribute check (list workflows by `TableUuid` through `temporal workflow list` in the admintools pod) is cheap and is a candidate.
