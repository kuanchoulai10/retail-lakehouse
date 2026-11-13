# Milestone 5: Spark Pools That Pull Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A maintenance attempt can run on a warm-on-demand Spark pool instead of its own SparkApplication: one Temporal task queue per size (S / M / L), one pool Deployment per size whose single pod runs Spark in local mode inside a Temporal worker, KEDA scaling each pool 0 → 1 on its queue's backlog and back to 0 when idle, a lost heartbeat classified like any failure (an OOM-killed pod is `oom`, the retry goes to the next size's queue) and the pod fenced (deleted and confirmed gone) before the retry.

**Architecture:** `TableMaintenanceWorkflow` stays the only dispatcher and keeps admission (limit 2, across both paths). For an attempt on the pool path it records the attempt start (backend activity), then starts the activity `run_pooled_maintenance_operation` on the size's queue; that activity is implemented by the Spark runtime's pool worker, not by the backend worker. The pool worker heartbeats with the pod's name, uid and Spark application id, runs the Iceberg procedure in a fresh `SparkSession` (the JVM and the downloaded jars stay warm between tasks), posts the result to the existing callback API and returns the same body. The workflow takes the first of the callback signal and the activity's own end. A heartbeat or deadline timeout is a new ending: the workflow records it (evidence read from that pod before it is touched), deletes that pod by name and uid, waits until it is gone, releases the slot and retries on the queue of the size the decision names. Which path a run uses is the setting `GLAC_SPARK__EXECUTION_PATH`, carried into the plan like `attempt_deadline_seconds`.

**Tech Stack:** Python 3.14 backend (Temporal Python SDK, Pydantic, kubernetes client), Spark runtime on `apache/spark:4.0.0` (PySpark local mode, Temporal Python SDK), Helm chart wave 25, KEDA 2.18 `temporal` scaler (available since 2.17), Temporal server 1.32.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` (section "5. Spark pools, reduced for minikube"); Linear KCL-61, KCL-62, KCL-63. A code map of the paths this plan touches is in `.superpowers/sdd/table-health-roadmap/m5-map.md`; read it before the code.

## Global Constraints

- Never two maintenance operations on one table at the same time: only the table's reconciliation workflow starts runs (ADR 0002). A pool takes one task at a time (`max_concurrent_activities=1`).
- Never resubmit while the previous attempt can still write: a pool attempt that ended without its own result (lost heartbeat, deadline, cancel) is fenced (that pod deleted and confirmed gone) before the slot is released and before the retry is sent.
- The admission limit (2) applies to every attempt on either path; an attempt holds its slot from before it is sent until it is fenced or ended.
- The result path does not fork: the pool posts the same callback body to the same route as a SparkApplication; the first result per `(operation, attempt)` wins.
- Failure classes, attempt limits and size escalation are milestone 2's (`classify_attempt_failure`, `decide_next_attempt`); the pool adds endings, not rules.
- `GLAC_SPARK__EXECUTION_PATH` = `spark_application` (default in code and chart) | `pool`. Pool defaults (`GLAC_SPARK__POOL__*`, chart `spark.pool:`): `start_timeout_seconds` 900 (time a task may wait in its queue, which covers a scale-up and a same-size task ahead of it), `heartbeat_timeout_seconds` 60, heartbeat interval 10 s (runtime), `idle_seconds` 300 (KEDA `cooldownPeriod`), `termination_grace_seconds` 3600 (a scale-down lets the running task finish).
- Task queues: `table-maintenance-pool-s`, `table-maintenance-pool-m`, `table-maintenance-pool-l`. Activity name: `run_pooled_maintenance_operation`. Both pinned in the backend's `test_wire_names.py` and, as the same literals, in a runtime test.
- Every workflow change that alters the command sequence of a running workflow goes behind `workflow.patched("pooled-spark-execution")`, with a replay test of a history recorded before it.
- Project rules: one object per file, `from __future__ import annotations`, StrEnum, ABC ports, DDD layering (lint-imports), no infrastructure terms in `application/` names (a pool pod is a "maintenance executor" there), TDD, every commit passes the backend's `pytest`, `ty check`, `ruff check .`, `ruff format --check`, `lint-imports`, the runtime's `pytest` and `ruff`, and the console's checks if touched.
- No new dependencies except `temporalio` in the Spark runtime, which the spec requires (a Temporal worker in the pool pod); pin it to the version in the backend's `uv.lock`. Never `kubectl patch configmap`. No explanatory comment blocks in `values.yaml`. Kubernetes labels per `platform/CLAUDE.md`.
- Progress, decisions and blockers go to the Linear issue they concern (KCL-61 pool worker and queues, KCL-62 KEDA, KCL-63 heartbeat, OOM and fencing) as comments in Traditional Chinese.

## Decisions taken by the main session (rulings)

- **Pool, not ScaledJob.** The spec asks for a Deployment per size; keep it. KEDA's `temporal` scaler, `queueTypes: activity`, `targetQueueSize: "1"`, `activationTargetQueueSize: "0"`, `minReplicaCount: 0`, `maxReplicaCount: 1`, `cooldownPeriod: idle_seconds`, `pollingInterval: 10`, endpoint `temporal-frontend.temporal.svc.cluster.local:7233`, namespace from `temporal.namespace`.
- **Scale-down never kills a task silently.** The backlog counts waiting tasks only, so KEDA may scale a pool to 0 while it runs one. The pool worker shuts down gracefully on SIGTERM (stops polling, finishes the running activity) within `terminationGracePeriodSeconds = termination_grace_seconds`. A task longer than that grace is killed, loses its heartbeat and is retried: a written risk, not prevented.
- **Fresh session per task.** The pool worker creates a `SparkSession` per task and stops it after posting the result (as `run_maintenance(stop=...)` does today); the JVM and jars stay loaded. Each task has its own Spark application id, so the event log check of milestone 2 keeps working per attempt.
- **Driver memory is the pool's.** Local mode has no executors; the pod's JVM gets the size's `driver_memory` (`--driver-memory` through `PYSPARK_SUBMIT_ARGS`, set before the first session) and the container memory limit is `driver_memory + spark.pool.memoryOverhead` (chart value, default `384Mi`), so a heap that does not fit is an OOMKilled container, which is the evidence the classifier reads.
- **Identity for fencing.** The pod's name and uid come from the downward API (`POD_NAME`, `POD_UID`); every heartbeat carries `{pod_name, pod_uid, execution_id}`. The workflow reads them from the timeout's `last_heartbeat_details`. A task that never heartbeated has nothing to fence (it never ran Spark).
- **New endings.** `heartbeat_lost` (heartbeat timeout) and the existing `timed_out` (schedule-to-start timeout: no pool took it; start-to-close: past the deadline). `heartbeat_lost` reads evidence from the named pod and trusts its container exits (`OOMKilled` in `state` or `last_state` is `oom`; an exit 137 without `OOMKilled` is not `oom` for this ending, because the fence or a scale-down also kills with 137). Evidence is read before the delete.
- **Fence a pool pod.** Delete that pod with a uid precondition and `grace_period_seconds=0`; "gone" means no pod with that uid exists (the Deployment makes a new one with a new uid). Same bounds as milestone 1's fence (`table_maintenance_fencing_policy.py`): after 15 minutes record `still_running`, keep the slot and keep checking every 5 minutes.
- **Path reaches the workflow through the plan.** `plan_table_maintenance` adds `execution_path` (and the pool timeouts) to the plan dict, as it adds `attempt_deadline_seconds`; a plan without it (histories in flight) means `spark_application`.
- **Default stays `spark_application` in this milestone's code.** The main session flips the chart value to `pool` only after the cluster verification below passes, and records it.

## Review Focus

1. A pool pod OOM-killed mid-task restarts its container and may pull the next queued task before the fence deletes it; that task then loses its heartbeat too and is fenced and retried. It must be classified from its own evidence (not `oom` unless its own container says so), and no table may ever run twice at once.
2. A callback that arrives, then the activity fails (or the reverse): the first result wins and the attempt is recorded once.
3. A scale-down (SIGTERM) during a task: the task finishes and reports; the next task waits in the queue and a new pod takes it.
4. Two attempts of different tables on the same size: the second waits in the queue holding its admission slot; `start_timeout_seconds` must cover the first one's run or the second times out as `timeout` and retries.
5. Replay: a history recorded before `pooled-spark-execution` replays without non-determinism, and the SparkApplication path's commands are unchanged when `execution_path` is absent or `spark_application`.

---

### Task 1: Settings, plan field and wire names

**Files:**
- Create: `backend/bootstrap/configs/spark_execution_path.py` (`SparkExecutionPath` StrEnum), `backend/bootstrap/configs/spark_pool_settings.py`
- Create: `backend/context/table_maintenance/adapter/hybrid/temporal/contracts/shared/pool_task_queue.py` (`pool_task_queue(size: str) -> str` and the three constants)
- Modify: `spark_settings.py` (fields `execution_path`, `pool`), `contracts/table_maintenance/activity.py` (`RUN_POOLED_MAINTENANCE_OPERATION`), `table_reconciliation_activities.py` (plan fields), chart `configmap.yaml` / `values.yaml`
- Test: `tests/bootstrap/configs/test_app_settings.py`, `contracts/test_wire_names.py`, the plan activity test

**Interfaces:**
- Produces: `SparkExecutionPath.SPARK_APPLICATION = "spark_application"`, `.POOL = "pool"`; `SparkPoolSettings(start_timeout_seconds=900, heartbeat_timeout_seconds=60, idle_seconds=300, termination_grace_seconds=3600)`; plan dict keys `execution_path`, `pool_start_timeout_seconds`, `pool_heartbeat_timeout_seconds`; `pool_task_queue("S") == "table-maintenance-pool-s"` (M, L likewise; unknown size raises `ValueError`).

- [ ] Tests: settings defaults and env override (`GLAC_SPARK__EXECUTION_PATH=pool`, `GLAC_SPARK__POOL__START_TIMEOUT_SECONDS=30`); wire names pin the three queues and the activity name; the plan carries `execution_path` from settings.
- [ ] Implement; chart: `spark.executionPath: spark_application`, `spark.pool: {startTimeoutSeconds, heartbeatTimeoutSeconds, idleSeconds, terminationGraceSeconds, memoryOverhead}` mapped in `configmap.yaml`.
- [ ] Commit `feat(table-maintenance): add the pool execution path setting and queue names`.

### Task 2: Pool endings, evidence from one pod, and fencing ports

**Files:**
- Modify: `AttemptEnding` (domain) and `MaintenanceAttemptEnding` (contract) + `HEARTBEAT_LOST = "heartbeat_lost"`; `classify_attempt_failure.py` (trusted exits for `heartbeat_lost`, the 137-without-`OOMKilled` rule above); `record_table_maintenance_operation_result.py` (`_ENDINGS_WITH_EVIDENCE`, pass the pod name and execution id); `ReadMaintenanceJobEvidenceGatewayInput` (optional `executor_name: str | None`) and its K8s adapter (read that pod, not by labels)
- Create: outbound ports `delete_maintenance_executor/` (`DeleteMaintenanceExecutorGateway.delete(input: executor_name, executor_uid)`) and `read_maintenance_executor/` (`ReadMaintenanceExecutorGateway.read(input) -> Output(present: bool)`), their K8s adapters, use cases + services `DeleteMaintenanceExecutor` / `GetMaintenanceExecutor`, fakes, `Gateways` + `fake_gateways()` entries, wiring
- Modify: chart `rbac.yaml` (worker Role: `pods` `delete`)

**Interfaces:**
- Produces: record input gains `executor_name: str | None`, `execution_id: str | None` (optional, default `None`); activities `delete_maintenance_executor` and `get_maintenance_executor` (names in `TableMaintenanceActivity`, pinned).

- [ ] Tests (classifier): `heartbeat_lost` with a container `OOMKilled` (in `last_state`) → `oom`; `heartbeat_lost` with exit 137 and no `OOMKilled` → `other`; `heartbeat_lost` with no evidence → `other`; existing rules unchanged.
- [ ] Tests (record service): a `heartbeat_lost` record reads evidence of the named pod and uses the given execution id for the event log check; the decision for `oom` at S is `retry_larger` to M.
- [ ] Tests (K8s adapters, `MagicMock` API): delete sends the uid precondition and grace 0, and a 404 is success; read is `present=False` for 404 and for a pod with another uid; evidence by `executor_name` reads that pod's `state` / `last_state`.
- [ ] Implement, regenerate nothing (no API change). Commit `feat(table-maintenance): classify and fence a lost pool attempt`.

### Task 3: Pool path in the maintenance workflow

**Files:**
- Modify: `table_maintenance_workflow.py` (attempt on the pool path, behind `workflow.patched("pooled-spark-execution")`), `table_reconciliation_activities.py` or a new activity `start_pooled_maintenance_attempt` that records the attempt start and returns the pool request (the submit service without the submit gateway; the request is the SparkApplication's `GLAC_REQUEST` content plus `size`)
- Create: `contracts/table_maintenance/pooled_operation_input.py` (`PooledMaintenanceOperationInput`: `request: dict`, `heartbeat_seconds: int`) and `pooled_operation_heartbeat.py` (`pod_name`, `pod_uid`, `execution_id`)
- Test: `test_table_maintenance_workflow.py` with scripted pool workers on the three queues (time-skipping env); a replay test of a pre-patch history (record one with the current code before changing it, as the existing fixtures were)

**Interfaces:**
- Consumes: Task 1 plan fields and queue names, Task 2 activities and endings.
- Produces: a pool attempt's job name is the pod that ran it: the record step stores `executor_name` (from the result, or the last heartbeat) as the attempt's job name when the attempt has none, so the API and console show it where they show a SparkApplication name today.
- Produces: on the pool path, `workflow.start_activity(RUN_POOLED_MAINTENANCE_OPERATION, input, task_queue=pool_task_queue(size), schedule_to_start_timeout=pool_start_timeout, start_to_close_timeout=attempt deadline, heartbeat_timeout=pool_heartbeat_timeout, retry_policy=RetryPolicy(maximum_attempts=1))`.

- [ ] Tests: a pool attempt that reports by callback succeeds, its activity's later return is ignored; one that returns without a callback succeeds from the return value; a heartbeat timeout records `heartbeat_lost` with the last heartbeat's pod, deletes that pod, waits until `get_maintenance_executor` says gone, then retries on the next size's queue after an `oom` decision (and the same queue after `other`); a schedule-to-start timeout records `timed_out` with nothing to fence; a cancel cancels the activity and fences the pod from the last heartbeat; the admission slot is held from before the activity starts until the fence ends; with `execution_path` absent the workflow issues exactly the SparkApplication path's commands; replay of the pre-patch fixture passes.
- [ ] Implement. Commit `feat(table-maintenance): run maintenance attempts on Spark pools`.

### Task 4: Pool worker in the Spark runtime

**Files:**
- Create in `runtime/spark/`: `pool_contract.py` (queue names and activity name, same literals as the backend), `local_session_conf.py` (the conf the SparkApplication passes today: extensions, REST catalog, s3a, event log, redaction, jars, from env), `pooled_operation.py` (the activity), `pool_heartbeat.py` (a background heartbeat thread), `pool_worker.py` (entry: worker on `GLAC_POOL_TASK_QUEUE`, `max_concurrent_activities=1`, graceful shutdown on SIGTERM)
- Modify: `Dockerfile` (install `temporalio` pinned; COPY the new modules), `pyproject.toml`, `tests/test_dockerfile.py` expectations if needed
- Test: `runtime/spark/tests/` (no JVM: Spark and Temporal faked)

**Interfaces:**
- Consumes: `PooledMaintenanceOperationInput` shape (Task 3); `run_maintenance(request, sql, measure=, stop=, post=)`; `post_result`.
- Produces: the activity returns the callback body plus `execution_id`; heartbeats `{pod_name, pod_uid, execution_id}` every `heartbeat_seconds`.

- [ ] Tests: the activity builds a `JobRequest` from the input, runs it with a fresh session, posts the callback and returns the body; it heartbeats while the procedure runs and stops after; a failing procedure posts and returns `succeeded=false` (the activity itself does not raise); `local_session_conf` matches the SparkApplication's conf keys (compare with the backend's `spark_application_manifest` values as literals in the test); the pool contract literals equal the backend's.
- [ ] Build the image locally and check `python3 -c "import temporalio, pyspark"` in it. Commit `feat(spark): add a pool worker that pulls maintenance tasks`.

### Task 5: Pool Deployments and KEDA ScaledObjects

**Files:**
- Create: chart `templates/spark-pool.yaml` (one Deployment per size in `namespaces.maintenanceOperations`, ServiceAccount `table-maintenance-spark`, command `python3 /opt/spark/work-dir/pool_worker.py`, env from the ConfigMap keys the pool needs plus the Polaris and S3 secrets, downward API `POD_NAME` / `POD_UID`, memory limit per the ruling, `terminationGracePeriodSeconds`), `templates/spark-pool-scaledobject.yaml`; render only when `spark.executionPath == "pool"` or `spark.pool.enabled` (pick one, say which)
- Modify: `validate.sh` of wave 25 if it lists objects; `platform/CLAUDE.md` wave 25 line
- Test: `helm template` checks in the chart's existing test style (or `scripts/tests` if the chart has none), label checker passes

- [ ] Tests: rendered with `executionPath: pool`, three Deployments and three ScaledObjects exist with the queue names, `minReplicaCount 0`, `maxReplicaCount 1`, `cooldownPeriod 300`, the memory limits; rendered with the default, none exist.
- [ ] Commit `feat(platform): deploy Spark pools scaled by queue backlog`.

### Task 6: Console and docs

- [ ] Console: wherever an attempt's ending or failure is shown, `heartbeat_lost` reads "Lost heartbeat"; a pool attempt shows the pod name where a SparkApplication name is shown today. No other console change.
- [ ] Docs: `docs/agents/project-history.md` milestone 5 line; `src/data-platform/backend/CLAUDE.md` (pool path, new endings, executor ports); `platform/CLAUDE.md` wave 25 (pools, KEDA); `docs/agents/known-follow-ups.md`: the risks you could not close (scale-down of a task longer than the grace, a restarted pod pulling a task before its fence, anything else).
- [ ] Do not change `e2e.sh` (the main session decides). Commit `docs(table-maintenance): record Spark pools`.

## Verification on the cluster (main session, after review)

**Deploy size: wave 25, then the final offboard / onboard and full e2e.**

1. **Scale from zero.** With `spark.executionPath: pool`, no pool pod exists while idle; the first S task scales `table-maintenance-pool-s` to 1 within the start timeout; after `idle_seconds` with no tasks it is 0 again.
2. **E2e on the pool path.** The full e2e passes with `executionPath: pool` (one Spark job at a time still holds).
3. **OOM escalation.** A table too large for S's driver memory: the S pod is OOMKilled, the attempt ends `heartbeat_lost` classified `oom`, that pod is deleted and confirmed gone before the M attempt is sent, and the M pool runs it.
4. **Lost heartbeat without OOM.** `kubectl delete pod --grace-period=0` on a busy pool pod: `heartbeat_lost`, class `other`, retried at the same size after the fence.
5. **Admission across pools.** Three tables due at once on different sizes: never more than two attempts hold slots.
6. Decide the chart default (`pool` if 1-5 pass), redeploy, restore any verification values with `git restore`, clean up tables, rules and policies.

**E2e decision for the main session:** suggested: the e2e asserts that a pool pod ran its compaction (the attempt's job name is a pool pod) when the path is `pool`, and nothing new when it is `spark_application`.
