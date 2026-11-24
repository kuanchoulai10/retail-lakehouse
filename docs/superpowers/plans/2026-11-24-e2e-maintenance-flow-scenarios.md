# Maintenance Flow E2e Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the cluster verifications of the maintenance flow (partition selection, one operation per run, queues and priorities, reconciliation triggers) into pytest e2e scenarios that run nightly on a platform deployed with a test values overlay.

**Architecture:** The wave-25 chart gains `values-e2e.yaml`, applied by `bootstrap.sh` when `SETTINGS_PROFILE=e2e`; the nightly gate deploys that profile, runs the full e2e and deploys the default back. Scenarios drive checks on demand with `POST /v1/tables/{uuid}/reconcile`, read Kubernetes through `KubernetesApi` with a second Role in `lakehouse-maintenance-operations`, and hold the normal Volcano queue with a pod-less PodGroup.

**Tech Stack:** pytest, httpx (Kubernetes watch streams), PyIceberg (`append`, `update_spec`), temporalio, Helm.

**Spec:** Linear KCL-105 (description and completion conditions), read 2026-11-24. Inventory of every check with its scenario or the reason it stays manual: `docs/superpowers/plans/2026-11-24-e2e-maintenance-flow-inventory.md` (row numbers below refer to it; the "Final mapping" section added in Task 8 is binding where it differs).

## Global Constraints

- Scenarios are black-box (contracts `e2e-black-box`, `e2e-not-imported`); no Trino; partition specs change with PyIceberg `update_spec()`.
- Every name comes from `OwnedNames`; every create pushes its undo right after it succeeds; every wait is a bounded `wait_until`, never a fixed sleep standing in for a condition.
- The test values are an overlay only: `values.yaml` defaults stay unchanged, and a deploy shows which profile it applied.
- A background writer is a thread with a stop event, stopped and joined by the first undo on the stack.
- "One job per table" counts every SparkApplication from ADDED to DELETED, so one with a `deletionTimestamp` still counts.
- A full round (`run.sh full`) stays under one hour.
- One object per file; `from __future__ import annotations`; ABC over Protocol.

## Review Focus

- A scenario cut short leaves no queue holder (it blocks every normal-queue run until removed): the sweep deletes holders by label, and the holder's undo is pushed right after its create.
- A scenario that needs the overlay fails at its start, naming the setting, when the platform runs the defaults; none passes because a wait happened to fit.
- The job watch cannot report "never two" because it saw nothing: it asserts it saw each run's job, and re-lists on a 410.
- The background writer stops on every path, and an append error fails the scenario instead of vanishing in the thread.
- The nightly gate deploys the default profile back even when the run fails.

## Rulings made while planning (the user delegated decisions)

- Ruling: overlay values `compactionQuietSeconds 60`, `compactionMaxQuietWaitSeconds 180`, `rewriteDataFilesCooldownSeconds 60`, `queueWaitLimitSeconds 900`; every other setting keeps its default — the inventory's Settings section gives each reason — cost if wrong: a scenario that needs another value fails at its start and the overlay gains a line.
- Ruling: 3.7 (queue wait does not count toward the attempt deadline) stays manual [cost] — it needs a 300 s attempt deadline that would time out any slow Spark job in every scenario, and adds 4 min to a round already near the hour; the deadline logic is unit-tested — cost if wrong: that path stays unit-tested only.
- Ruling: the queue holder is a pod-less PodGroup (`minResources` cpu 2, memory 2304Mi, queue `table-maintenance`), not a pod — spike 2026-11-24 on the cluster: the holder went `Inqueue`, a second PodGroup with the same request stayed `Pending`, and went `Inqueue` within 15 s of the holder's delete. Creating pods would let the e2e run as any ServiceAccount of that namespace — cost if wrong: if a Spark PodGroup is not held the same way, E falls back to a real blocker job.
- Ruling: Role in `lakehouse-maintenance-operations` for `table-maintenance-e2e`: `sparkapplications` get/list/watch, `podgroups` get/list/create/delete, `pods` get/list; nothing cluster-scoped — cost if wrong: one more rule.
- Ruling: the profile is chosen at deploy: `SETTINGS_PROFILE=default|e2e` (anything else fails before any cluster call); the overlay sets `settingsProfile: e2e`, which labels the ConfigMap `retail-lakehouse.io/settings-profile`; `bootstrap.sh` prints the profile; `gates:nightly:e2e-full-test` deploys wave 25 with `e2e`, runs `run.sh full`, and deploys `default` back in a `defer` — the cluster is shared with development, and leaving the short cooldowns on is the "forgot to change it back" the issue removes — cost if wrong: two wave-25 deploys per nightly, a few minutes outside the round.
- Ruling: `critical` gains only API checks (B: 1.2, 2.8 and 2.12 404s, 3.2, 4.6); every scenario that waits on discovery, a reconciliation or a Spark job is `full` (KCL-104's rule), which is how "one or two of the fastest as critical" is met — cost if wrong: pre-merge runs no Spark job.
- Ruling: no parallel scenario workers unless a measured round exceeds one hour; the normal queue admits one job at a time, so parallelism buys little — cost if wrong: a later task splits the round.

---

### Task 1: The test values overlay and the settings profile

**Files:** Create `platform/25-lakehouse-control-plane/chart/values-e2e.yaml`; Modify `chart/values.yaml` (`settingsProfile: default`), `chart/templates/configmap.yaml` (label), `bootstrap.sh` (profile check first, `-f`, print), `tasks/gates/nightly/nightly.yml` (`e2e-full-test` deploys e2e, defers default), `tasks/apps.yml` (an internal task that runs only the wave-25 bootstrap and validate with a profile); Test `scripts/tests/test_control_plane_settings_profile.py`.

- [ ] Test first: `helm template` of the chart renders the ConfigMap with the default values and label `default`; with `-f values-e2e.yaml` the four overlay values and label `e2e`, every other key equal to the default render; `SETTINGS_PROFILE=bogus bash bootstrap.sh` exits non-zero with `SETTINGS_PROFILE must be default or e2e` and runs no `kubectl`/`helm`. Watch it fail, implement, green.
- [ ] Deploy with the `e2e` profile on the cluster, read the ConfigMap label and `/v1/platform-settings`, deploy `default` back.
- [ ] `task gates:pre-pr` green; commit `feat(platform): a settings profile for the e2e platform (KCL-105)`.

### Task 2: Support for jobs, queue holders, writers and settings

**Files:** Modify `e2e/support/kubernetes_api.py` (`get`, `list`, `watch`, `create`, `delete` on a namespaced resource path); Create `e2e/support/spark_job_watch.py`, `queue_holder.py`, `background_writer.py`, `require_settings.py`; Modify `owned_names.py` (`queue_holder(suffix, scenario)`, pattern `QUEUE_HOLDER`), `sweep_leftovers.py` (holders), `conftest.py` (`kubernetes` fixture), `platform/25-lakehouse-control-plane/e2e/rbac.yaml` (second Role and RoleBinding); Tests in `tests/e2e_support/`.

**Interfaces:**
- `KubernetesApi.list(path, label_selector=None) -> dict`, `.get(path) -> dict | None`, `.create(path, body) -> dict`, `.delete(path) -> None` (404 is fine), `.watch(path, resource_version, stop: threading.Event) -> Iterator[dict]` (one decoded event per line; a 410 raises `WatchExpired`).
- `SparkJobWatch.start(kubernetes, run_ids: Callable[[], set[str]]) -> SparkJobWatch`, `.stop()`, `.most_at_once -> int`, `.seen_run_ids -> list[str]` (first appearance order), `.names -> dict[str, str]` (run id -> job name); live set from ADDED until DELETED; on `WatchExpired` re-lists and resumes.
- `QueueHolder.create(kubernetes, cleanup, name) -> QueueHolder`, `.release()` (idempotent; the pushed undo calls it).
- `BackgroundWriter.start(table, rows: Callable[[int], pa.Table], every_seconds) -> BackgroundWriter`, `.stop() -> int` (appends made; re-raises the first append error).
- `require_settings(platform, **at_most: int) -> dict[str, int]`: fails with `"<key> is <value>, needs at most <n>: deploy with SETTINGS_PROFILE=e2e"`.

- [ ] Tests first for each (MockTransport for Kubernetes, including a watch whose MODIFIED with `deletionTimestamp` keeps the job live and a 410 that re-lists; a writer whose append raises; the sweep deleting a holder PodGroup by label). Watch them fail, implement, green.
- [ ] Apply the Role on the cluster and check `kubectl auth can-i` as the ServiceAccount: the listed verbs yes, `create pods` and anything cluster-scoped no.
- [ ] Commit `feat(e2e): watch Spark jobs, hold the queue, write in the background (KCL-105)`.

### Task 3: Critical API checks and the manual run's extra checks

**Files:** Modify `e2e/test_maintenance_policies.py` (1.2), `e2e/test_removed_routes.py` (2.8 404, 3.2), Create `e2e/test_maintenance_requests_refused.py` (2.12 404, 4.6), Modify `e2e/test_manual_maintenance.py` (2.1, 2.3, 2.6a, 2.8, 2.9, 2.12, 3.5, 4.2, 6.3, 6.4).

- [ ] Write the checks from the inventory rows; `run.sh critical` and the manual module on the cluster; green twice; commit `test(e2e): maintenance request refusals and the manual run's jobs (KCL-105)`.

### Task 4: Partition cap, order and spec evolution

**Files:** Create `e2e/test_partition_cap_and_order.py` (1.5-1.8, 2.5), `e2e/test_partition_spec_evolution.py` (1.11); Modify `e2e/test_scheduled_partition_compaction.py` (commit window 90 s, row H).

- [ ] Each overlay-dependent module calls `require_settings` in its first fixture. Run on the cluster with the e2e profile; commit `test(e2e): partition cap, order and spec evolution scenarios (KCL-105)`.

### Task 5: Quiet period and the longest wait

**Files:** Create `e2e/test_partition_quiet_and_max_wait.py` (1.8, 1.9, 1.10) with `BackgroundWriter` on `hot`.

- [ ] Commit `test(e2e): quiet period and longest wait scenario (KCL-105)`.

### Task 6: The queue and stopping midway

**Files:** Create `e2e/test_maintenance_queue.py` (3.3, 3.4, 3.6, 4.3, 4.4, 4.5, 2.6b) with `QueueHolder`; `e2e/test_maintenance_cancel.py` (2.7).

- [ ] The queue module first waits until the namespace has no SparkApplication; it asserts its own run's PodGroup is `Pending` behind the holder before it relies on the hold. Commit `test(e2e): queue priority and cancel scenarios (KCL-105)`.

### Task 7: Reconciliation triggers

**Files:** Create `e2e/test_reconciliation_triggers.py` (5.3, 5.5, 5.6, 5.8).

- [ ] Commit `test(e2e): reconciliation trigger scenarios (KCL-105)`.

### Task 8: Docs, two rounds, close

- [ ] Inventory: "Final mapping" section. Docs: wave 25 README (profile, overlay, the second Role, the holder, new scenarios, round time), backend `CLAUDE.md` E2e section, `project-history.md`.
- [ ] `task gates:nightly:e2e-full-test KUBE_CONTEXT=retail-lakehouse` twice: both pass, `run.sh full` under one hour each; afterwards the profile label is `default`, no e2e pod, no queue holder, no SparkApplication of an e2e table, no `tm_e2e_catalog_*`, `tm-e2e-*` policy or `e2e_*` namespace, no running writer (the pod is gone), one ready worker.
- [ ] Commit `docs(e2e): the maintenance flow scenarios (KCL-105)`; final review; Linear comment, Done.
