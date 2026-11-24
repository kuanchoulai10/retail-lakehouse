# KCL-105 inventory: maintenance-flow cluster checks to move into pytest e2e scenarios

Written 2026-11-24 from the plans in `docs/superpowers/plans/`, the Linear comments on KCL-92, KCL-93, KCL-94 and KCL-95
(read through the Linear MCP on 2026-11-24: the 2026-11-22 run notes on KCL-94 and KCL-95, the 2026-11-20 notes on KCL-92
and KCL-93), the KCL-105 description, the KCL-104 inventory (`2026-11-24-e2e-policy-discovery-inventory.md`, its rows
marked `KCL-105`) and the code at `main` (129593ce). Nothing was run on a cluster.

## Reading guide

* **Class.** `AUTO-critical` = API answers only, seconds, no managed table (KCL-104's binding rule: a scenario that waits
  for discovery to manage a table, a reconciliation, a Spark job or a restart is `full`). `AUTO-full` = nightly.
  `MANUAL` = stays manual, with a reason tag: `[visual]` a person judges it; `[infra]` deployment validation that
  `apps:validate` / `validate.sh` own; `[superseded]` the step, script or feature is gone; `[logs]` reads pod logs and
  judges them; `[cost]` the only way to provoke it costs more than the round's budget or needs crafted data.
  `covered` = an existing scenario already asserts it (named).
* **Scenario letters** (proposed modules, see "Proposed scenarios"): **C** = extend `test_manual_maintenance.py`,
  **D1** `test_partition_cap_and_order.py`, **D2** `test_partition_quiet_and_max_wait.py`, **D3**
  `test_partition_spec_evolution.py`, **E** `test_maintenance_queue.py`, **F** `test_maintenance_cancel.py`, **G**
  `test_reconciliation_triggers.py`, **B** critical API checks (added to `test_removed_routes.py` and
  `test_maintenance_policies.py`, or a new `test_maintenance_requests_refused.py`).
* **"Settings" column.** The platform setting a check depends on and the value it needs; "policy" means a value the
  scenario sets in its own maintenance policy (no platform setting). "none" = runs under the defaults.
* **Driving checks.** Every plan that is not a manual run applies the full assessment, partition selection and cooldowns
  included: `schedule`, `catalog_commit`, `table_managed`, `policy_changed` and `reconcile_now`
  (`PlanTableMaintenanceService.execute`: only `manual_operations` skips the assessment). So a scenario triggers a
  "scheduled" check on demand with `POST /v1/tables/{uuid}/reconcile` (202) and needs no schedule or commit-window wait,
  except where the window or the schedule is itself the check (G). Runs started by such a plan have `trigger:
  "scheduled"`.
* **Black-box surfaces.** API `/v1/...` (`PlatformApi`), PyIceberg writes and `inspect.files()`, Temporal client
  (`TemporalSession`: describe, list, cancel), Kubernetes API through `KubernetesApi` with the pod's ServiceAccount (needs
  the Role in "Kubernetes access"). A SparkApplication carries no table label: a scenario ties a job to its table by the
  label `table-maintenance/run-id` against the table's run ids (`GET /v1/tables/{uuid}/table-maintenance-runs`); every run
  of a plan exists, `pending`, before its first submit, so the ids are known before any job.
* **Policy floors.** `on.schedule.every_seconds` is 60 to 604800; `on.catalog_commit.debounce_seconds` 0 to 86400
  (`ScheduleTrigger`, `CatalogCommitTrigger`). Leaving `catalog_commit` out means commits open no window, so a scenario
  that drives checks with `reconcile` should leave it out and set `every_seconds: 3600`.

## Plan wording that differs from the code today

| plan says | code does now |
|---|---|
| KCL-94: a run records `filters: [{spec_id, where}]`; KCL-95: plus `procedure_args` | the run API has `partitions: [{spec_id, fields: [{column, transform}], partitions: [[value, ...]]}]` and `settings` (job content, ADR 0016); the `where` text exists only in the Spark adapter (`spark_where_clauses`). Assert partition values, not `where` strings |
| KCL-94: selection order is "most reducible files first" | partitions over the target for at least `max_quiet_wait` come first (oldest `since` first), then the rest by reducible files, then spec id and `repr(values)` (`select_compaction_partitions`) |
| KCL-94: the longest wait counts from when the partition went over the target | it counts from the first plan that saw it over the target (an untracked partition's `since` is `now`); the 2026-11-22 run saw the same (about one check interval later) |
| KCL-94 step 5: "the commit-window check about 60 s later records `waiting_for_writes`" | any non-manual plan does, `reconcile_now` included; `next_eligible_at = min(last_written_at + quiet, since + max_wait)`; a partition's last write ignores compaction (`replace`) snapshots and is null once its adding snapshot expired (then it never waits) |
| KCL-94 steps 4-6: Trino `INSERT`, `capped$files`, `ALTER TABLE ... SET PROPERTIES partitioning` | e2e talks to no query engine: PyIceberg appends, `inspect.files()`, `update_spec()` (the 2026-11-22 run did the same) |
| KCL-94 step 6: "driver log shows two `CALL`s" | black-box substitute: the run lists two spec entries and succeeds, and the files of both specs drop |
| KCL-95: "the child workflow creates every run `pending` before its first submit" | the parent reconciliation creates all runs of a plan in one transaction (`CREATE_MAINTENANCE_RUNS`) before it starts the child; a refused child start skips them with "the table's maintenance workflow could not be started" |
| KCL-95 check 3: "the requeued attempt's job name changes" | the name is `tm-<op code>-<run suffix>-a<attempt>` and a requeue keeps the attempt number, so the name stays the same (Linear 2026-11-22) |
| KCL-95 check 4: `temporal workflow cancel` CLI | the e2e cancels with the Temporal client (`get_workflow_handle("table-maintenance:table-uuid=<uuid>").cancel()`); run 1 itself ends `failed` with an attempt ended `cancelled`, later runs `skipped` with "the table's maintenance stopped before this run started" |
| KCL-95 check 5: "the api pod log shows `POST .../result` 2xx" | black-box substitute: each run `succeeded` with procedure metrics and no `completed_without_callback`; the old path `/v1/table-maintenance-runs/{id}/operations/{op}/result` is 404 |
| KCL-92 plan and its first comment: driver/executor pods carry `table-maintenance-p<N>` | only the PodGroup carries the class (`batchSchedulerOptions.priorityClassName`); pods have none (KCL-92 comment of 2026-11-20, README) |
| KCL-92 step 3: "with an admission slot free" | admission is gone (KCL-93); each Volcano queue admits one job of any size (every size asks cpu 2, the cap is cpu 2) |
| KCL-93 plan: "the reconciliation starts one child per run" | one child per plan, running one run per operation, one at a time (KCL-95) |
| KCL-93 Task 6: "an attempt still queued at the limit is fenced" | it is polled once more at the limit: a job read running or completed then runs on; otherwise fenced, `queue_timed_out` |
| KCL-93 step 4: `temporal workflow list` in the admin-tools pod | Temporal client `list_workflows('TableUuid = "<uuid>" AND ExecutionStatus = "Running"')` |
| Reconciliation-records plan: wake reasons `settings_changed`, `resumed`, `paused`; skip reasons `paused`, `excluded`; a per-table dry-run setting; a record-level `run_id` | wake reasons are `schedule`, `catalog_commit`, `table_managed`, `policy_changed`, `manual_run`, `reconcile_now`, `previous_run_finished`; results add `needs_attention`, `waiting_for_writes`; dry run is the policy's `dry_run`; each operation carries its own `run_id` |
| Plans watch with `kubectl get sparkapplications -w` | the e2e reaches Kubernetes only through `e2e/support/kubernetes_api.py` (httpx + ServiceAccount token), which today knows only the worker Deployment; it needs list/watch helpers and the Role below |
| Milestone 3/4 plans: compaction candidates, rounds, budget, SLA, `GrantedTableUuids`; milestone 2: `/health`, `/mappings` | all removed (KCL-93, KCL-98) |
| Plans use `every_seconds: 300` for "scheduled" | the floor is 60 s, and a `reconcile` call needs no schedule at all |

---

## Source 1. `2026-11-20-partition-selected-compaction.md` Task 10 (KCL-94)

2026-11-22 manual result (Linear): 7 passed, e2e and console not run.

| # | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|
| 1.1 | Rebuild, `apps:validate` exits 0 | -- | MANUAL [infra] | -- | -- |
| 1.2 | Platform settings have the group "Compaction partition selection" with the cap, quiet period and longest wait, between cooldowns and discovery | `GET /v1/platform-settings`: group keys in order `execution_capacity, compute_sizes, cooldown_and_backoff, partition_selection, discovery`; the three items `maintenance_compaction_partitions_per_job`, `..._quiet_seconds`, `..._max_quiet_wait_seconds` equal the pod's own `GLAC_MAINTENANCE_COMPACTION_*` env (the e2e pod mounts `table-maintenance-config`), so it passes under either values file | AUTO-critical | none | B (`test_maintenance_policies.py`) |
| 1.3 | Console Platform settings page shows "10 partitions", "2 min", "1 h" | -- | MANUAL [visual] | -- | -- |
| 1.4 | Lower the cooldown and max wait by editing `values.yaml` and rerunning `bootstrap.sh` | replaced by the e2e values overlay (see Settings) | MANUAL [superseded] | -- | -- |
| 1.5 | Cap and order: of 12 partitions, 11 over the target; the first job takes the 10 with most reducible files (`r03`..`r12`) | Table identity(`region`), policy `rewrite_data_files {target {reducible_files {at_most 1}, per partition}, options {min_input_files 2}}`, `on {schedule 3600}`, no `catalog_commit`. 13 PyIceberg appends, append k writes one row into every `rNN` with `NN + 1 >= k`, so `rNN` holds `NN + 1` files. After the quiet period `POST .../reconcile`; wait for the run: `partitions[0].partitions` = `r03`..`r12` (set equality), `spec_id 0`; its reconciliation's `rewrite_data_files` measurements `qualifying_partitions 11`, `selected_partitions 10`, `waiting_partitions 0`, result `started`, `run_id` = the run. After it: `inspect.files()` has 1 data file in each of `r03`..`r12`, `r01` 2, `r02` 3 | AUTO-full | quiet 60 s; cap 10 (default) | D1 |
| 1.6 | The Overview's reducible files drop after the compaction (also KCL-104 4.6) | `GET .../metrics/current` `reducible_files` and `data_files` before run 1 and after the next check (1.7) are lower by the files rewritten | AUTO-full | as 1.5 | D1 |
| 1.7 | The rest goes next time: the next check after the cooldown compacts `r02` alone | `POST .../reconcile` right after run 1 ends: record shows `rewrite_data_files` `cooling_down` with `next_eligible_at` = about end + cooldown (skip this assert if the expire run of 2.5 already outlasted the cooldown); poll `reconcile` until a new compaction run starts: `partitions` = `[["r02"]]` | AUTO-full | rewrite cooldown 60 s | D1 |
| 1.8 | A freshly written partition waits the quiet period | Right after the D1 appends, `POST .../reconcile`: record `rewrite_data_files` `waiting_for_writes`, `next_eligible_at` within 5 s of last append + quiet, `selected_partitions 0`, `waiting_partitions 11`, no new run | AUTO-full | quiet 60 s (must exceed the reconcile latency, a few seconds) | D1 |
| 1.9 | A quiet partition is compacted while a written one waits | Table identity(`region`), same policy. 4 appends into `cold`; `reconcile` -> `waiting_for_writes`. Start the background writer on `hot` (3 appends, then one every 15 s). After `cold`'s quiet period, `reconcile`: run partitions `[["cold"]]`, record `selected_partitions 1`, `waiting_partitions 1` | AUTO-full | quiet 60 s; max wait 180 s (hot must not be overdue about 70 s after it was first seen) | D2 |
| 1.10 | A partition written all the time is compacted after the longest wait, and the writes see no commit conflict | Writer keeps going; after the cold run and its cooldown, `reconcile` every 20 s until a run names `hot`: its plan time is at least the first record that showed `hot` waiting + max wait; the run `succeeded` at attempt 1, `metrics.failed_data_files_count` 0 when present; the writer thread raised nothing (every append committed); stop the writer (first undo on the stack) and join it | AUTO-full | max wait 180 s; cooldown 60 s; quiet 60 s (above the 15 s write gap) | D2 |
| 1.11 | A table whose spec changed gets one entry per spec (day + bucket, then day only) | Table `day(ts), bucket(id, 4)`; 3 appends each covering 2 days x 2 buckets; `update_spec()` removing the bucket field; 3 appends into one day. After the quiet period `reconcile`: run `partitions` has two entries, spec 0 with fields `[ts day, id bucket[4]]` and spec 1 with `[ts day]`; run `succeeded`; afterwards `inspect.files()` shows fewer files in both specs | AUTO-full | quiet 60 s | D3 |
| 1.12 | The driver log shows two `CALL`s | 1.11 is the black-box form | MANUAL [logs] | -- | -- |
| 1.13 | A manual compaction is the whole table | `partitions == []` on the manual `rewrite_data_files` run | covered (`test_manual_maintenance.py`) | none | -- |
| 1.14 | The partition value with a quote (`o'neil`) is compacted (e2e step 8) | -- | covered (`test_scheduled_partition_compaction.py`) | -- | -- |
| 1.15 | Console Maintenance tab Scope lines, phone width; Reconciliations tab "Waiting for writes" copy | -- | MANUAL [visual] | -- | -- |
| 1.16 | Restore `values.yaml`, `e2e.sh`, `gates:pre-pr`, record on Linear | -- | MANUAL [superseded] | -- | -- |

## Source 2. `2026-11-21-one-operation-per-run.md` Task 12 (KCL-95)

2026-11-22 manual result (Linear): first round found two Spark jobs of one table at once for a few seconds (fixed in
514dd50e / 4cd20e3e); rerun polled 163 times, never two; each hand-over left about 30 s with no job.

| # | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|
| 2.1 | A manual run of four operations makes four runs at once, all `pending` | Right after `POST .../maintenance` poll `runs(uuid)` until four new manual runs exist; at first sight they share one `created_at` and one `execution_ref`, and runs 2-4 are `pending` (run 1 may already be `queued`) | AUTO-full | none | C |
| 2.2 | The runs run in the fixed order, each starting after the previous finished | -- | covered (`test_manual_maintenance.py`) | -- | -- |
| 2.3 | A table never has two SparkApplications at any time, one being deleted included; each run's job is gone before the next one's appears | Before the POST open a watch (`GET /apis/sparkoperator.k8s.io/v1beta2/namespaces/lakehouse-maintenance-operations/sparkapplications?watch=true&resourceVersion=<list rv>`) in a thread; keep the set of live objects whose `table-maintenance/run-id` label is one of this table's run ids (live from ADDED until DELETED, so a MODIFIED with `deletionTimestamp` still counts); assert the set never exceeds 1 and the run ids appear in plan order; re-list on a 410. Stop the thread in cleanup | AUTO-full | none | C (needs Role) |
| 2.4 | The reconciliation links each operation to its own run | -- | covered (`test_manual_maintenance.py`) | -- | -- |
| 2.5 | A scheduled plan with two operations due gives one reconciliation, two runs, two links, compaction first | D1's policy also has `expire_snapshots {target {min_snapshots_to_keep 1, max_snapshot_age_seconds 60}}`; the check of 1.5 then plans both: one record with two `started` operations, each `run_id` a different run, `trigger "scheduled"`, both `succeeded`, expire `started_at >= ` compaction `finished_at`; also KCL-104 3.9's timing half (expiry runs once a snapshot is old enough) and, on the 1.7 check, `expire_snapshots` `cooling_down` | AUTO-full | quiet 60 s (the 60 s snapshot age passes during it); expire cooldown default (21600) | D1 |
| 2.6a | A raise reaches every unfinished run of the plan, and starts no new run | While run 1 or 2 of the C plan is in flight, `POST .../maintenance {"operations": ["rewrite_data_files"], "priority": "P1"}`: afterwards the runs not finished at the raise read `priority "P1"`, finished ones `P3`, and no run beyond the four appears for that table (post early: a raise arriving after the last attempt ended is given back as a new plan) | AUTO-full | none | C |
| 2.6b | A queued run raised to P0 is requeued: same attempt, same job name, urgent queue | see 3.5 | AUTO-full | see 3.5 | E |
| 2.7 | Stopping midway turns the later runs `skipped` with the reason, none stays `pending` | Dry-run table, manual `rewrite_data_files, rewrite_manifests, expire_snapshots`; wait until run 1 has an attempt (`queued` or `running`); cancel `table-maintenance:table-uuid=<uuid>` through Temporal; poll: run 1 `failed`, its attempt `ended_by`/status shows the cancel; runs 2, 3 `skipped`, `skip_reason` = "the table's maintenance stopped before this run started"; no run `pending`; no SparkApplication with these run ids left (list); the reconciliation workflow still running (`reconciliation_running`) | AUTO-full | none | F (needs Role, list) |
| 2.8 | Results reach the new callback path | Every run of C `succeeded` with procedure metrics (`rewritten_data_files_count` etc.) and none has `metrics.completed_without_callback` (only `POST /v1/table-maintenance-runs/{id}/result` accepts results); the old path `POST /v1/table-maintenance-runs/{mr-id}/operations/rewrite_data_files/result` answers 404 | AUTO-full (C) + AUTO-critical (404 half, B) | none | C, B |
| 2.9 | The maintenance execution's summary and `MaintenanceOperations` list every operation of the plan; `TableUuid` finds it | After C's plan: `describe()` of `table-maintenance:table-uuid=<uuid>`: search attribute `MaintenanceOperations` = the four operations, `static_summary` = `<table name> · rewrite_data_files, rewrite_manifests, expire_snapshots, remove_orphan_files` (check the SDK exposes `static_summary`); `TableUuid` half already in `_assert_found_by_table` | AUTO-full | none | C |
| 2.10 | Console side panels at 1280 and 390 px, url parameters, focus, "No attempt yet", "belongs to another table" | -- | MANUAL [visual] | -- | -- |
| 2.11 | `e2e.sh`, `gates:pre-pr`, record on Linear | -- | MANUAL [superseded] | -- | -- |
| 2.12 | `GET /v1/table-reconciliations/{id}` reads one record; an unknown id is 404 | C: each record from the list equals `GET /v1/table-reconciliations/{id}`; B: a well-formed unknown `rc-` id -> 404 | AUTO-full + AUTO-critical | none | C, B |

## Source 3. `2026-11-20-per-table-maintenance-workflow.md` Task 14 (KCL-93)

2026-11-20 manual result (Linear): all passed; Trino scaled to 0 for the queueing checks.

| # | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|
| 3.1 | Rebuild, `validate.sh`; no admission workflow, no `compaction-rounds` schedule | -- | MANUAL [infra] | -- | -- |
| 3.2 | Removed routes answer 404 | `/v1/compaction-rounds` covered by KCL-104 2.8; add `GET /v1/compaction-rounds/{id}`, `GET /v1/scheduler-settings`, `GET /v1/tables/{random uuid}/compaction-candidates` -> 404 with FastAPI's `{"detail": "Not Found"}` | AUTO-critical | none | B (`test_removed_routes.py`) |
| 3.3 | Several tables due at once queue by priority: a later P1 run goes before an earlier P3 one | E: with the queue held, manual P3 on `c`, then `PUT /v1/tables/{b}/priority {"priority":"P1"}` (answer `priority "P1"`, `GET /v1/tables/{b}` agrees) and manual on `b` without a priority; release the hold: `b`'s attempt `started_running_at` < `c`'s, and `b`'s run `priority "P1"` | AUTO-full | none (holder) | E |
| 3.4 | Waiting runs read `queued` | E: while held, `b` and `c` runs read `queued`, their attempt `status "queued"`, `started_running_at null`; their PodGroups `status.phase` is `Pending` or `Inqueue` | AUTO-full | none | E |
| 3.5 | One table never runs two maintenance workflows; a reconcile-now while one runs starts no second | C: during the plan `list_workflows('TableUuid = "<uuid>" AND ExecutionStatus = "Running" AND WorkflowType = "TableMaintenanceWorkflow"')` lists exactly one, id `table-maintenance:table-uuid=<uuid>`; `POST .../reconcile` during the plan; still one; its `reconcile_now` record appears only after the plan's runs ended (`reconciled_at >=` last run's `finished_at`) | AUTO-full | none | C |
| 3.6 | A P0 manual run resubmits a waiting P3 run into the urgent queue at once; attempt stays 1; no second run row | E: manual P3 on `d` while held; when its attempt is `queued`, `POST .../maintenance {"operations":["rewrite_data_files"],"priority":"P0"}`: `d`'s run `priority "P0"`, `attempts` length 1, attempt 1; the SparkApplication with `d`'s run id has the same name and `spec.batchSchedulerOptions` `queue "table-maintenance-urgent"`, `priorityClassName "table-maintenance-p0"`; its PodGroup `spec.queue` urgent; `d`'s `started_running_at` is set while the hold is still in place; no new run for `d` | AUTO-full | none (holder) | E |
| 3.7 | Queue wait does not count toward the attempt deadline | E: keep the hold until `b`'s and `c`'s attempts have been queued longer than the deadline + 10 s; both runs `succeeded` at attempt 1 with `started_running_at - started_at > attempt deadline` and `finished_at - started_running_at < attempt deadline` | AUTO-full | attempt deadline 300 s (and queue wait limit above the longest wait, 900 s) | E (optional part) |
| 3.8 | `e2e.sh` with Trino back | -- | MANUAL [superseded] | -- | -- |
| 3.9 | An attempt still queued at the queue wait limit ends `queue_timed_out`, not retried (KCL-93 constraint, not in Task 14) | would need a hold longer than the queue wait limit (>= 900 s with the proposed value, or a limit short enough to break 3.3-3.7); unit-tested in the workflow tests | MANUAL [cost] | -- | -- |

## Source 4. `2026-11-19-table-priority-volcano-queues.md` Task 9 (KCL-92)

2026-11-19/20 manual results (Linear): passed; P4 refused 422; pods no longer carry the class.

| # | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|
| 4.1 | Rebuild; both queues `Open` with capability cpu 2 / 5017Mi; four PriorityClasses, `preemptionPolicy Never` | cluster-scoped objects; `validate.sh` checks them | MANUAL [infra] | -- | -- |
| 4.2 | A run's PodGroup is in `table-maintenance` with class `table-maintenance-p3` and the size's resources; pods use Volcano and carry no class | C: for run 1's job read the PodGroup (`spark-<app name>-pg`; confirm the operator's name, else list by owner): `spec.queue "table-maintenance"`, `spec.priorityClassName "table-maintenance-p3"`, `spec.minResources` `cpu "2"`, `memory "2304Mi"` (S); its pods (`labelSelector=table-maintenance/run-id=<id>`): `spec.schedulerName "volcano"`, no `priorityClassName` | AUTO-full | none | C (needs Role) |
| 4.3 | Two P3 runs at once: one runs, the other waits until it ends | E: after the release, never two normal-queue jobs with a driver running at once (compare `b` and `c` attempt times: `c.started_running_at >= b.finished_at`) | AUTO-full | none | E |
| 4.4 | With a P3 job holding the normal queue, a P0 run goes at once in the urgent queue | = 3.6 (the holder plays the P3 job) | AUTO-full | none | E |
| 4.5 | A table set to P1 runs with class `table-maintenance-p1` | E: `b`'s SparkApplication `priorityClassName "table-maintenance-p1"`, queue `table-maintenance` | AUTO-full | none | E |
| 4.6 | An unknown priority is refused | `PUT /v1/tables/{random uuid}/priority {"priority":"P4"}` -> 422 (body validated before the lookup); `POST /v1/tables/{random uuid}/maintenance {"operations":["rewrite_data_files"],"priority":"P9"}` -> 422 | AUTO-critical | none | B |
| 4.7 | Console priority select | -- | MANUAL [visual] | -- | -- |

## Source 5. `2026-11-10-reconciliation-records.md` Tasks 12-13, and KCL-104's deferred timing rows

| # | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|
| 5.1 | Wait for idle runs, deploy, migrate Job created the table | -- | MANUAL [infra] | -- | -- |
| 5.2 | Terminate and restart the reconciliation workflows after the deploy | the no-migration rule rebuilds the cluster instead | MANUAL [superseded] | -- | -- |
| 5.3 | A table's reconciliations show a `schedule` record within one interval | G: policy `on {schedule {every_seconds 60}, ...}`; poll (<= 150 s) for a record with `wake_reasons.schedule >= 1` | AUTO-full | policy 60 s | G |
| 5.4 | Reconcile now adds a record within a minute | -- | covered (`test_manual_maintenance.py`) | -- | -- |
| 5.5 | Inserts add a `catalog_commit` record (KCL-104 3.7: 10 commits within a minute give exactly one record after the debounce, counting them) | G: dry-run table, policy `catalog_commit {debounce_seconds 30}`, `rewrite_data_files per table at_most 1`; 10 PyIceberg appends in a burst; poll: exactly one new record with `catalog_commit`, its count == 10 (confirm the event path counts each commit once), `reconciled_at` between first commit + 30 s and + 60 s | AUTO-full | policy 30 s debounce | G |
| 5.6 | Dry run: a check with something due records `would_start` and starts no run | G: the 5.5 record has `dry_run true`, `rewrite_data_files` `would_start`, `run_id null`; `runs(uuid)` empty | AUTO-full | none | G |
| 5.7 | A manual run in dry run still starts and the record links it | -- | covered (`test_manual_maintenance.py`) | -- | -- |
| 5.8 | KCL-104 3.8 timing half: with `catalog_commit` removed, inserts open no window until the schedule | G: `PUT` the policy to `on {schedule {every_seconds 60}}`; 3 appends; the next new record has `schedule` and no `catalog_commit` key | AUTO-full | policy 60 s | G |
| 5.9 | The drawer at phone width | -- | MANUAL [visual] | -- | -- |
| 5.10 | `checks:e2e-full-test`, rebuild and full retest | -- | MANUAL [superseded] | -- | -- |

KCL-104's other `KCL-105` rows: 3.9 timing half -> 2.5; 4.6 -> 1.6; 7.10 -> 6.4.

## Source 6. Other plans with cluster checks of the same kind

| # | plan / step | check (plain words) | how a black-box scenario checks it | class | settings | scenario |
|---|---|---|---|---|---|---|
| 6.1 | `2026-11-13-milestone-1-timeout-fencing.md` steps 2-3 | A timed-out attempt is fenced: no live pod of attempt N when attempt N+1's job is created | needs a job that runs longer than the attempt deadline, which cannot be made reliably (a Spark job is 1-2 min; lowering the deadline under that breaks every other scenario) | MANUAL [cost] | -- | -- |
| 6.2 | same, step 4 | `TableUuid` search finds the reconciliation and the run | -- | covered (`_assert_found_by_table`) | -- | -- |
| 6.3 | `2026-11-13-milestone-2-failure-classes-and-oom.md` step 1 | A normal job runs at size S: attempt `size "S"`, `event_log_finished true`; driver `terminationMessagePolicy FallbackToLogsOnError`; requests about 1152Mi | size and event log covered by `assert_runs_succeeded`; C adds the pod read: driver container `terminationMessagePolicy` and `resources.requests.memory` (768m + 384Mi overhead) | AUTO-full | none | C |
| 6.4 | `2026-11-19-prefixed-resource-ids.md` Task 9 (KCL-104 7.10) | Spark application names use the run suffix | C watcher: every SparkApplication name is `tm-<rdf/rm/es/rof>-<run id suffix>-a<attempt>`, labels `table-maintenance/run-id`, `/operation`, `/attempt` match, and the run's `attempts[].job_name` equals it | AUTO-full | none | C |
| 6.5 | milestone 2 steps 2-5 | An OOM at S retries at M; OOM at L marks `needs_attention`, cleared by a new policy | needs about 1.2 GB of crafted data and a sizes change | MANUAL [cost] | -- | -- |
| 6.6 | `2026-11-13-milestone-3-partition-candidates.md`, `-4-priorities-and-budget.md` | candidates top N, held/too_small, budget rounds, SLA, `GrantedTableUuids` | features removed by KCL-93 | MANUAL [superseded] | -- | -- |

---

## Settings

Every value bounds a wait; all are `AppSettings` fields read from the `table-maintenance-config` ConfigMap through
`envFrom`, so **every one is read once, at process start** (api and worker alike): a change needs a redeploy. `helm
upgrade` with a changed value rolls both Deployments (`checksum/config` annotation on their pod templates). What differs
is when the running worker applies the value it holds:

* **per plan** (next check after the restart): the cooldowns (`build_operation_cooldowns` -> `PlanTableMaintenanceService`)
  and partition selection (`build_partition_selection_settings` -> `PlanTableMaintenanceService`);
* **per run, frozen at plan time**: attempt deadline, max attempts, queue wait limit (`build_activities` ->
  `TableReconciliationActivities` -> plan output -> `TableMaintenanceWorkflowInput`); a run in flight keeps the values of
  its plan;
* **per schedule sync**: discovery interval (`build_gateways` -> `SyncDiscoverySchedulesTemporalGateway`), written into a
  schedule when it is created or updated (worker start, or an attachment change in that catalog);
* `GET /v1/platform-settings` answers from the api process's own env (`build_platform_settings`), so it shows the worker's
  values only once both have rolled.

| setting | Helm key | env var | default | where the code reads it | proposed e2e value | why that value |
|---|---|---|---|---|---|---|
| compaction quiet period | `worker.compactionQuietSeconds` | `GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS` | 120 | `bootstrap/container/build_partition_selection_settings.py` | **60** | a scenario must post `reconcile` and read `waiting_for_writes` inside it (latency a few seconds), and D2's writer (every 15 s) must stay inside it; 60 s keeps 4x margin and halves every quiet wait (D1, D2, D3, `test_scheduled_partition_compaction.py`) |
| longest wait for quiet | `worker.compactionMaxQuietWaitSeconds` | `GLAC_MAINTENANCE_COMPACTION_MAX_QUIET_WAIT_SECONDS` | 3600 | same | **180** | must be above quiet (60) and above the time from `hot`'s first sighting to the plan that compacts `cold` (about 70 s), so D2 can see `hot` still waiting; 180 s leaves about 110 s margin and bounds D2's wait to 3 min |
| partitions per job | `worker.compactionPartitionsPerJob` | `GLAC_MAINTENANCE_COMPACTION_PARTITIONS_PER_JOB` | 10 | same | **10 (unchanged)** | 13 appends make 11 partitions over the target, so the default cap is tested as is |
| compaction cooldown | `worker.rewriteDataFilesCooldownSeconds` | `GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS` | 3600 | `bootstrap/container/build_operation_cooldowns.py` (counted from the attempt's recorded end, `OperationState.last_attempt_at`) | **60** | "the rest next time" (1.7) and the hot run (1.10) need a second compaction of one table; 60 s is long enough that a check posted right after a run still reads `cooling_down` |
| manifest / expiry cooldown, orphan interval, backoff cap | `worker.rewriteManifestsCooldownSeconds`, `expireSnapshotsCooldownSeconds`, `removeOrphanFilesIntervalSeconds`, `failureBackoffCapSeconds` | `GLAC_MAINTENANCE_REWRITE_MANIFESTS_COOLDOWN_SECONDS`, `..._EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS`, `..._REMOVE_ORPHAN_FILES_INTERVAL_SECONDS`, `..._FAILURE_BACKOFF_CAP_SECONDS` | 21600, 21600, 604800, 86400 | same | **unchanged** | no check runs one of these twice on a table (manual runs ignore cooldowns); D1 relies on the expiry cooldown to read `cooling_down` |
| attempt deadline | `worker.attemptDeadlineSeconds` | `GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS` | 21600 | `bootstrap/container/build_activities.py` | **300** (only if 3.7 is kept; else unchanged) | 3.7 needs a queue wait longer than the deadline, so the hold is deadline + 10 s; 300 s is about 2.5x the slowest observed driver run. Risk: any job whose driver runs over 300 s times out in every scenario; if one does, use 600 and a 610 s hold (+5 min) or drop 3.7 |
| queue wait limit | `worker.queueWaitLimitSeconds` | `GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS` | 86400 | same | **900** | no check needs it short; a stuck queue then fails a run in 15 min instead of 24 h, which keeps the round bounded. Must stay above E's longest wait (`c`: hold 310 s + `b`'s run, about 450 s) |
| max attempts | `worker.maxAttempts` | `GLAC_MAINTENANCE_MAX_ATTEMPTS` | 3 | same | unchanged | -- |
| discovery interval | `worker.discoveryIntervalSeconds` | `GLAC_DISCOVERY_INTERVAL_SECONDS` | 600 | `bootstrap/container/build_gateways.py` | unchanged | attach, detach and policy saves rescan at once; no KCL-105 check waits for the schedule |
| maintenance schedule / commit window | -- (policy `on.schedule.every_seconds`, `on.catalog_commit.debounce_seconds`) | -- | policy | `ScheduleTrigger` (60-604800), `CatalogCommitTrigger` (0-86400) | per scenario | not a platform setting: "shorten the schedule intervals" in KCL-105 is done in each scenario's policy |

The overlay holds only `worker.compactionQuietSeconds`, `worker.compactionMaxQuietWaitSeconds`,
`worker.rewriteDataFilesCooldownSeconds`, `worker.queueWaitLimitSeconds` and (with 3.7) `worker.attemptDeadlineSeconds`.
To make the profile visible: a scenario module that needs it reads `/v1/platform-settings` at its start and fails at once
naming the value it needs (better than a 20-minute timeout); a ConfigMap label or a non-`GLAC_` key (for example
`E2E_VALUES_PROFILE`) shows it in `kubectl get configmap` (a `GLAC_` key that is no `AppSettings` field is ignored by
pydantic-settings, but keep it out of that prefix anyway).

## Kubernetes access

Today: ServiceAccount `table-maintenance-e2e` (ns `lakehouse-control-plane`), Role with `apps/deployments`
`get, patch` on `table-maintenance-worker` (`platform/25-lakehouse-control-plane/e2e/rbac.yaml`); the pod mounts the
token. Nothing cluster-scoped is needed: queues and PriorityClasses stay with `validate.sh` (4.1).

A second Role + RoleBinding, both in namespace **`lakehouse-maintenance-operations`**, subject the same ServiceAccount:

| apiGroup | resource | verbs | used by |
|---|---|---|---|
| `sparkoperator.k8s.io` | `sparkapplications` | `get`, `list`, `watch` | 2.3, 2.7, 3.6, 4.5, 6.4 (watch for one-job-per-table; list for "none left"; get for `batchSchedulerOptions`) |
| `scheduling.volcano.sh` | `podgroups` | `get`, `list` | 3.4, 3.6, 4.2 |
| `""` | `pods` | `get`, `list` | 4.2, 6.3 (schedulerName, no priorityClassName, terminationMessagePolicy, requests; by label `table-maintenance/run-id`) |
| `scheduling.volcano.sh` | `podgroups` | `create`, `delete` (+ the `list` above for the sweep) | E queue holder only |
| `""` | `pods` | `create`, `delete` | E queue holder only |

**Queue holder (E).** A PodGroup (`scheduling.volcano.sh/v1beta1`, `minMember 1`, `queue table-maintenance`,
`minResources {cpu: "2"}`) and one pod (`schedulerName volcano`, annotation `scheduling.k8s.io/group-name`, image from the
pod's own `GLAC_SPARK__IMAGE` / `GLAC_SPARK__IMAGE_PULL_POLICY` env, `command ["sleep", "3600"]`, no ServiceAccount token,
requests `cpu 100m`, labels `app.kubernetes.io/name: table-maintenance-e2e-queue-holder` plus the run suffix). It plays
"another job holding the queue" for as long as the scenario wants, which makes 3.3-3.7 deterministic. Any positive cpu
request should block a cpu-2 job against a cpu-2 capability; **confirm in a spike** that Volcano keeps a Spark PodGroup
Pending behind it (if not, request `cpu "2"`, the footprint of one S job). Undo deletes both (pushed right after create);
the session sweep deletes holders by that label (needs the `list` and `delete` above). Without a holder, 3.3-3.6 need a
real Spark job on a blocker table (a 60-90 s window, timing-dependent) and 3.7 cannot be done.

`KubernetesApi` needs, besides its Deployment methods: `list(group, version, namespace, resource, label_selector)`, a
streaming `watch(...)` (httpx stream, `?watch=true&resourceVersion=`), `get`, and `create` / `delete` for the holder.

## Proposed scenarios and time budget

Spark job about 1-2 min start to finish (1.5 used below); a managed table about 20-30 s to create and manage; cleanup about
30-45 s per table. The existing full round: 37 scenarios, about 24 min.

| scenario | marker | checks | est. wall time | settings it needs |
|---|---|---|---|---|
| B: critical API checks (`test_maintenance_policies.py`, `test_removed_routes.py` or a new module) | critical | 1.2, 2.8 (404), 2.12 (404), 3.2, 4.6 | ~5 s | none |
| C: extend `test_manual_maintenance.py` | full | 2.1, 2.3, 2.6a, 2.8, 2.9, 2.12, 3.5, 4.2, 6.3, 6.4 | +~1 min (no extra Spark run) | none |
| D1 `test_partition_cap_and_order.py` | full | 1.5-1.8, 2.5 (and KCL-104 3.9 timing, 4.6) | ~8 min (setup 1, waiting record and quiet 1, compaction 1.5 + expiry 1.5, `r02` run 1.5, reads 0.5, cleanup 0.7) | quiet 60, cooldown 60 |
| D2 `test_partition_quiet_and_max_wait.py` | full | 1.8, 1.9, 1.10 | ~6.5 min (setup 1, quiet 1, cold run 1.5, until overdue and cooldown about 0.5, hot run 1.5, cleanup 1) | quiet 60, max wait 180, cooldown 60 |
| D3 `test_partition_spec_evolution.py` | full | 1.11 | ~4 min | quiet 60 |
| E `test_maintenance_queue.py` | full | 3.3-3.7, 4.3-4.5, 2.6b | ~11.5 min with 3.7 (setup 3 tables 1.5, hold 5.3 with `d` running inside it, `b` 1.5, `c` 1.5, cleanup 1.5); ~7.5 min without 3.7 | holder; deadline 300 and queue limit 900 for 3.7 |
| F `test_maintenance_cancel.py` | full | 2.7 | ~3 min | none |
| G `test_reconciliation_triggers.py` | full | 5.3, 5.5, 5.6, 5.8 | ~4 min (no Spark) | policy values only |
| H: change `test_scheduled_partition_compaction.py`'s policy to `catalog_commit {debounce_seconds 90}` | full | (existing) | -~3.5 min: today its 60 s window closes inside the quiet period, so the compaction waits for the 300 s schedule | quiet 60 |

Total added: 0.1 + 1 + 8 + 6.5 + 4 + 11.5 + 3 + 4 - 3.5 ≈ **34.6 min**, so the full round ≈ **58-59 min**: inside one hour
with almost no margin. **Flag:** the round goes over the hour if Spark jobs run nearer 2 min than 1.5 (each of the about 10
added jobs adds 30 s). In order: drop 3.7 (-4 min, also removes the risky deadline value); then run D1, D2, D3, F and G in
parallel workers (each owns its tables). Parallelism helps less than it seems: the normal Volcano queue admits one job at a
time, so Spark time stays serial, and E must run alone (it assumes an empty queue and holds it). C and E both read the
namespace, so the other scenarios must not run Spark jobs while E holds the queue.

Isolation notes: E and C first wait until the namespace has no SparkApplication of another table (a dev cluster with a
managed CDC table would otherwise interfere). D2's writer is a thread with a stop event, stopped by the first undo on the
stack and joined, so a failed scenario leaves no writer.

## What can run under default settings

* **critical, under any values (deployed as is):** B (1.2 compares the API with the pod's own env, so it holds for the
  defaults and the overlay; 2.8 and 2.12 404s; 3.2; 4.6).
* **full but needing no shortened setting:** C (manual runs ignore cooldowns and quiet), F, G (policy values only), E
  without 3.7 (needs only the holder and its Role), D3 (works with the default 120 s quiet, +1 min), and D1's 1.5, 1.6,
  1.8 and 2.5 (+1 min). Of these, B is the only one that fits `critical` by KCL-104's rule; F is the fastest full one (about
  3 min, no Spark run finishes) if a second `critical` is wanted, but it needs discovery to manage a table.
* **needing the overlay:** 1.7 (cooldown 3600 s by default), 1.9 and 1.10 (max wait 3600 s), 3.7 (deadline 21600 s).

## Counts

Rows per class in the source tables (a row split into a full and a critical half counts once, in its main class):

* AUTO-critical: 3 rows (1.2, 3.2, 4.6), plus the critical halves of 2.8 and 2.12.
* AUTO-full: 31 rows (1.5-1.11 = 7; 2.1, 2.3, 2.5, 2.6a, 2.6b, 2.7, 2.8, 2.9, 2.12 = 9; 3.3-3.7 = 5; 4.2-4.5 = 4; 5.3, 5.5,
  5.6, 5.8 = 4; 6.3, 6.4 = 2). 3.7 is optional (it needs the 300 s deadline); 4.4 duplicates 3.6.
* MANUAL: 20 rows (visual 5: 1.3, 1.15, 2.10, 4.7, 5.9; infra 4: 1.1, 3.1, 4.1, 5.1; superseded 7: 1.4, 1.16, 2.11, 3.8,
  5.2, 5.10, 6.6; logs 1: 1.12; cost 3: 3.9, 6.1, 6.5).
* covered by existing scenarios: 7 rows (1.13, 1.14, 2.2, 2.4, 5.4, 5.7, 6.2).

## Final mapping

Written 2026-11-24 once the scenarios landed. Every `AUTO` row above is a scenario except 3.7, which the plan's ruling
kept manual [cost] (it needs a 300 s attempt deadline that would time out slow jobs in every other scenario).

| scenario | marker | rows it verifies |
|---|---|---|
| `test_maintenance_policies.py` (partition selection settings) | critical | 1.2 |
| `test_removed_routes.py` (four more routes) | critical | 3.2, the 404 halves of 2.8 and 2.12 |
| `test_maintenance_requests_refused.py` | critical | 4.6, the 404 half of 2.8 |
| `test_manual_maintenance.py` (jobs, PodGroup, workflow, raise) | full | 2.1, 2.3, 2.6a, 2.8, 2.9, 2.12, 3.5, 4.2, 6.3, 6.4 |
| `test_partition_cap_and_order.py` | full | 1.5, 1.6, 1.7, 1.8, 2.5 (and KCL-104's 3.9 timing) |
| `test_partition_quiet_and_max_wait.py` | full | 1.8, 1.9, 1.10 |
| `test_partition_spec_evolution.py` | full | 1.11 (spec 1's own file count is not asserted: rewritten files go under the current spec) |
| `test_maintenance_queue.py` | full | 2.6b, 3.3, 3.4, 3.6, 4.3, 4.4, 4.5 |
| `test_maintenance_cancel.py` | full | 2.7 |
| `test_reconciliation_triggers.py` | full | 5.3, 5.5, 5.6, 5.8 |
| `test_scheduled_partition_compaction.py` (commit window 90 s) | full | (existing rows 1.14; the round is shorter) |

Two platform findings came out of the first cluster rounds. The queue scenario found that a raise could replace a job
the Spark operator was still submitting, after which the old submit created the driver under the shared name and the
replacement failed; it is fixed (a job with no state reads `SUBMITTING` and is not replaced). The cap scenario found that
partial progress can drop a partition's commit while the run reads `succeeded`; it is in `docs/agents/known-follow-ups.md`,
and the scenario turns partial progress off in its own policy.
