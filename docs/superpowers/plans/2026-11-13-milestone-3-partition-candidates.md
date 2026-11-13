# Milestone 3: partition candidates, benefit / cost scores, top N per run — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** reconcile turns the partitions that need compaction into persisted, scored candidates; a scheduled compaction run takes only the top N of them, sized by their data, with fewer partitions after an out-of-memory attempt; the console shows every candidate's benefit, cost, score, state and why it was not picked.

**Architecture:** a new aggregate `CompactionCandidate` (one per table and partition, own SQL table) in the table maintenance context. `PlanTableMaintenanceService` keeps observing and assessing as today, then syncs the candidates from the qualifying partitions (domain service), ranks the pending ones, claims the top N for the run id the reconciliation workflow already creates before planning, and plans `rewrite_data_files` for exactly those partitions. The run's result moves the claimed candidates on (fast path); the next observation decides (the table wins). Scores use fixed reference bounds so they mean the same on every table (milestone 4 ranks across tables).

**Tech Stack:** Python 3.13, pydantic domain models, SQLAlchemy Core repos, Temporal Python SDK (`workflow.patched`), PyIceberg 0.10, FastAPI, React + Orval client, Storybook stories.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` (section "3. Candidates and scoring"; "Correctness: the table decides"). Linear issues KCL-53..57 hold the design decisions under "## 設計決定（2026-11-13）".

## Global Constraints

- Score = 0.7 × benefit + 0.3 × cost term, both normalised to [0, 1]; benefit = small files removable (the existing `compute_reducible_files` of the partition); cost = estimated GB·hours = memory GB of the size × data bytes ÷ throughput; higher cost lowers the score (cost term = 1 − normalised cost). Weights configurable.
- Normalisation uses fixed reference bounds, never the spread inside one table: `benefit_norm = min(1, reducible_files / benefit_reference_files)`, `cost_norm = min(1, gb_hours / cost_reference_gb_hours)`. The score is computed at observation and stored on the candidate.
- Throughput comes from run history (succeeded `rewrite_data_files` operations: `rewritten_bytes_count` over the succeeded attempt's duration) with a fixed default until history exists.
- Candidates sit under the policy, they do not replace it: a partition becomes a candidate only if it meets the policy's compaction conditions (today `reducible_files.at_least`, applied per partition as in `_measure_compaction`); the small and recently-written filters apply on top. A whole-table policy (`scope.unit == table`), a policy with no condition, or an unpartitioned table has one candidate standing for the whole table. The policy editor's meaning does not change.
- States `pending → claimed → running → done / failed`, with a lease on `claimed` / `running`; plus `held` for a partition that qualifies but is filtered (reason `too_small` or `recently_written`). A partition the next observation finds healthy (no longer qualifying) leaves the candidates whatever Spark reported; one still unhealthy after `done` / `failed`, or whose lease expired, is `pending` again.
- One run compacts only the top N pending candidates of its table by score (N configurable). Manual runs keep planning the whole table (unchanged); they neither claim nor change candidates.
- One operation per table at a time still holds (the reconciliation workflow stays the only dispatcher, ADR 0002).
- Observation is built full-scan first (Tasks 1–10 must work on the full scan alone). Incremental observation is Task 11, bounded: if its edge cases (expired remembered snapshot, compaction's own snapshots, delete files) do not come out clean within that task, ship the full scan and write "large tables are slow to observe" as a risk on KCL-53.
- Project rules: TDD, one object per file, `from __future__ import annotations`, StrEnum, ABC ports, DDD layering (`lint-imports`), every commit passes `pytest`, `ty check`, `ruff check .`, `lint-imports`, and the console's unit and story tests when the console changes. No new dependency. No comment blocks in `values.yaml`. Workflow changes replay old histories (`workflow.patched`).

## Review Focus

1. **A partition whose candidate row is claimed by a run that never started** (start failed, or the plan was emptied by `dry_run`): the claim must be released, or the partition sits out until its lease expires. Test: `test_start_failure_releases_the_claimed_candidates` (Task 6).
2. **Partition evolution and unpartitioned tables:** two specs with the same values tuple are different candidates (key includes `spec_id`); an unpartitioned table or a whole-table policy yields exactly one candidate whose plan is the whole table. Tests in Tasks 3 and 6.
3. **Lease expiry while the run is still live** (a run longer than its lease): reconcile must not hand the same partition to a second run while the first can still write — the per-table single dispatcher already prevents a second run on the table; the test pins that an expired lease turns the row `pending` but no new run is planned while a run is in flight. Test: `test_expired_lease_does_not_plan_while_a_run_is_in_flight` (Task 6).
4. **Spark reports success but the partition is still unhealthy** (writers added files again, or partial progress committed only some groups): the next observation sets it `pending` again with a fresh score. Test: `test_done_candidate_still_qualifying_is_pending_again` (Task 4).
5. **History with zero or missing durations / bytes** (lost callback `completed_without_callback`, an attempt without `finished_at`): throughput ignores such operations and never divides by zero. Test: `test_throughput_ignores_operations_without_bytes_or_duration` (Task 5).

---

### Task 1: partitions carry the time of their last write

**Files:**
- Modify: `context/table_maintenance/application/domain/model/shared/partition_stats.py` (field), `adapter/outbound/table/pyiceberg/observation_mapper.py` (`_partition_stats`), `application/port/outbound/table/read_table_metadata/table_metadata_observation.py` and `application/service/table/table_observation_from_gateway.py` (carry it through)
- Test: `tests/context/table_maintenance/adapter/outbound/table/pyiceberg/test_observation_mapper.py`, the gateway-conversion test

**Interfaces:**
- Produces: `PartitionStats.last_written_at: datetime | None = None` — the latest `timestamp_ms` (UTC) of the snapshots that added a live data or delete file of that partition (manifest entry `snapshot_id` → `table.metadata.snapshot_by_id(...).timestamp_ms`); `None` when unknown.

- [ ] Write `test_partition_last_written_at_is_the_newest_adding_snapshot` (two snapshots add files to partition A, one to B; A gets the later timestamp, B the earlier) and `test_last_written_at_is_none_when_the_snapshot_is_gone`; run, see them fail.
- [ ] Implement; run the observation and health tests; commit `feat(table-maintenance): record when each partition was last written`.

### Task 2: the `CompactionCandidate` aggregate

**Files:**
- Create under `application/domain/model/compaction_candidate/`: `compaction_candidate.py`, `compaction_candidate_id.py`, `candidate_state.py`, `hold_reason.py`, `partition_key.py`, `candidate_score.py`, `invalid_candidate_transition.py`, `__init__.py`
- Test: `tests/context/table_maintenance/application/domain/model/compaction_candidate/`

**Interfaces:**
- Produces:
  - `PartitionKey(spec_id: int, values: tuple[str | int | float | bool | None, ...])` with `whole_table() -> PartitionKey` (spec_id `-1`, values `()`) and `canonical() -> str` (stable JSON of `[spec_id, values]`, the unique column).
  - `CandidateState(StrEnum)`: `pending`, `held`, `claimed`, `running`, `done`, `failed`. `HoldReason(StrEnum)`: `too_small`, `recently_written`.
  - `CandidateScore(reducible_files: int, data_bytes: int, estimated_gb_hours: float, score: float)` (frozen; `0 <= score <= 1`).
  - `CompactionCandidate(AggregateRoot)`: `id`, `table_uuid`, `partition: PartitionKey`, `state`, `hold_reason: HoldReason | None`, `score: CandidateScore`, `last_written_at`, `observed_at`, `claimed_by_run_id: str | None`, `lease_expires_at: datetime | None`, `updated_at`. Methods: `observe(score, last_written_at, hold_reason, now)` (pending or held by the reason; a `done` / `failed` row becomes pending; a claimed / running row with a live lease keeps its state and only takes the new score; an expired lease becomes pending), `claim(run_id, lease_until, now)` (pending only), `start(run_id, now)` (claimed → running, same run only), `finish(run_id, succeeded: bool, now)` (claimed / running of that run → done / failed; other runs ignored), `release(run_id, now)` (claimed of that run → pending). Invalid moves raise `InvalidCandidateTransition`.

- [ ] Write the state tests first (each transition, the lease rule in `observe`, `finish` of another run is a no-op, `PartitionKey.canonical()` differs for the same values under two spec ids); run, see them fail.
- [ ] Implement; full domain tests pass; commit `feat(table-maintenance): add the compaction candidate aggregate`.

### Task 3: persist candidates

**Files:**
- Create: `application/port/outbound/compaction_candidate/compaction_candidates_repo.py`; `adapter/outbound/compaction_candidate/sql/{compaction_candidates_table.py, compaction_candidate_row_mapper.py, compaction_candidates_sql_repo.py, __init__.py}`; in-memory fake under tests
- Modify: `adapter/outbound/shared/sql/create_schema.py` (`AGGREGATE_SQL_PACKAGES`), `bootstrap/container/repositories.py`, `build_repositories.py`
- Test: `tests/.../adapter/outbound/compaction_candidate/test_compaction_candidates_sql_repo.py` (fixture `params=["sql", "memory"]`, as the reconciliation repo test), `test_create_schema.py` drift test

**Interfaces:**
- Produces: `CompactionCandidatesRepo(ABC)`: `list_by_table(table_uuid) -> list[CompactionCandidate]`, `list_by_run(run_id) -> list[CompactionCandidate]`, `save_all(candidates: Sequence[CompactionCandidate]) -> None` (upsert by `(table_uuid, partition.canonical())`), `delete(ids: Sequence[CompactionCandidateId]) -> None`, `delete_by_table(table_uuid) -> None`. Table `compaction_candidates`, unique `(table_uuid, partition_key)`, index on `(table_uuid, state)` and on `claimed_by_run_id`.

- [ ] Repo tests first (round trip of every field incl. `None`s, upsert keeps one row per key, two spec ids with equal values are two rows, `list_by_run`, delete); run, see them fail.
- [ ] Implement, register, wire; run the repo, schema and architecture tests; commit `feat(table-maintenance): persist compaction candidates`.

### Task 4: score and sync candidates from an observation

**Files:**
- Create: `application/domain/service/compaction_candidate/score_candidate.py`, `sync_compaction_candidates.py`, `candidate_scoring.py` (settings value object), `candidate_filters.py` (value object), `observed_partition.py` (value object), `__init__.py`
- Test: `tests/.../application/domain/service/compaction_candidate/`

**Interfaces:**
- Consumes: `PartitionStats` (+ `last_written_at`), `compute_reducible_files`, `CompactionCandidate`.
- Produces:
  - `CandidateScoring(benefit_weight: float = 0.7, cost_weight: float = 0.3, benefit_reference_files: int = 100, cost_reference_gb_hours: float = 1.0)`.
  - `CandidateFilters(min_partition_bytes: int, quiet_seconds: int)`.
  - `score_candidate(reducible_files: int, data_bytes: int, memory_gb: float, throughput_bytes_per_hour: float, scoring: CandidateScoring) -> CandidateScore` with `gb_hours = memory_gb * data_bytes / throughput_bytes_per_hour` and the Global Constraints formula.
  - `ObservedPartition(partition: PartitionKey, stats: PartitionStats, reducible_files: int)`.
  - `sync_compaction_candidates(table_uuid, existing: Sequence[CompactionCandidate], observed: Sequence[ObservedPartition], *, scoring, filters, memory_gb, throughput_bytes_per_hour, now) -> CandidateSync` where `CandidateSync(saved: tuple[CompactionCandidate, ...], removed: tuple[CompactionCandidateId, ...], next_check_at: datetime | None)`: new partitions are created, existing ones `observe`d, existing ones not in `observed` are removed (healthy → leave); `held(too_small)` when `data_bytes < min_partition_bytes`; `held(recently_written)` when `last_written_at` is within `quiet_seconds` of `now`, and `next_check_at` is the earliest moment such a hold ends.

- [ ] Tests first: `test_score_weights_benefit_and_cost` (exact values for one case, e.g. 50 files / 100 ref → benefit 0.5; 0.5 GB·h / 1.0 ref → cost term 0.5; score 0.5), `test_cost_above_reference_scores_zero_cost_term`, `test_score_is_the_same_for_the_same_partition_on_any_table`, `test_new_qualifying_partition_becomes_pending`, `test_partition_no_longer_qualifying_is_removed`, `test_done_candidate_still_qualifying_is_pending_again`, `test_small_partition_is_held_too_small`, `test_recent_partition_is_held_and_sets_next_check`, `test_claimed_candidate_with_live_lease_keeps_its_claim`; run, see them fail.
- [ ] Implement; commit `feat(table-maintenance): score compaction candidates and sync them from an observation`.

### Task 5: throughput from run history

**Files:**
- Create: `application/domain/service/compaction_candidate/estimate_throughput.py`
- Modify: `application/port/outbound/table_maintenance_run/table_maintenance_runs_repo.py` only if a new query is needed (prefer `list_by_table(table_uuid, limit)`)
- Test: `tests/.../domain/service/compaction_candidate/test_estimate_throughput.py`

**Interfaces:**
- Produces: `estimate_throughput(runs: Sequence[TableMaintenanceRun], *, default_bytes_per_hour: float, max_samples: int = 10) -> float` — bytes per hour over the newest `max_samples` succeeded `rewrite_data_files` operations with `rewritten_bytes_count > 0` and a succeeded attempt with both timestamps (sum of bytes ÷ sum of hours); `default_bytes_per_hour` when none qualify.

- [ ] Tests first: `test_throughput_is_bytes_over_hours_of_succeeded_compactions`, `test_throughput_falls_back_to_the_default_without_history`, `test_throughput_ignores_operations_without_bytes_or_duration` (Review Focus 5); run, see them fail.
- [ ] Implement; commit `feat(table-maintenance): estimate compaction throughput from past runs`.

### Task 6: reconcile syncs candidates and claims the top N for the run

**Files:**
- Modify: `application/service/table/plan_table_maintenance.py` (+ its inbound input/output), `application/domain/service/table/assess_maintenance.py` (expose the qualifying partitions and their reducible counts to the service, or return `ObservedPartition`s; keep the health output unchanged), `adapter/hybrid/temporal/inbound/workflows/table_reconciliation_workflow.py` (pass `run_id` to `PLAN_TABLE_MAINTENANCE`; on start failure or an empty / dry-run plan, call a release), activities and contracts for a `RELEASE_COMPACTION_CANDIDATES` activity, `bootstrap/container/build_use_cases.py`
- Create: `application/domain/service/compaction_candidate/select_top_candidates.py`, `application/domain/service/shared/size_for_bytes.py`, `application/service/compaction_candidate/release_compaction_candidates.py` (+ inbound port)
- Test: the plan service tests, workflow tests, new domain tests

**Interfaces:**
- Consumes: Tasks 2–5. `run_id` is the id the reconciliation workflow already generates before planning (`_plan_and_start_once`); passing it in the activity input is replay-safe (activity input payloads are not compared on replay), but guard any new command (the release activity) with `workflow.patched("release-unstarted-candidates")`.
- Produces:
  - `select_top_candidates(candidates, n: int) -> tuple[CompactionCandidate, ...]` — pending only, highest score first, ties by larger `reducible_files`, then `partition.canonical()`.
  - `size_for_bytes(data_bytes: int, *, s_max_bytes: int, m_max_bytes: int) -> ComputeSize`. The planned `start_size` = the larger of the table's remembered size and `size_for_bytes(sum of selected data bytes)`.
  - The plan's `rewrite_data_files` entry covers exactly the selected partitions (`build_partition_filters` over their stats; the whole-table candidate plans the whole table). Each selected candidate is `claim`ed with `lease_until = now + attempts × attempt_deadline + 1 h` and saved before the activity returns. The plan output gains `candidate_partitions: list[{spec_id, values}]` (for the record and the console) and `filter_sets` (Task 7).
  - `ReleaseCompactionCandidatesService.execute(run_id)` → every candidate claimed by that run back to `pending`.
  - Nothing pending (all held / claimed) → compaction is not planned this round; the reconciliation's outcome for compaction says why (new result values `all_held` / `all_claimed`, wording in Task 9). `next_check_at` from the sync feeds the workflow's next wake like `next_eligible_at`.

- [ ] Tests first: `test_plan_takes_only_the_top_n_candidates` (5 qualifying partitions, N = 2, the plan's filters cover exactly the two best), `test_plan_claims_the_selected_candidates_for_the_run`, `test_start_size_covers_the_selected_bytes` (remembered S, 2 GiB selected → L), `test_start_failure_releases_the_claimed_candidates` (Review Focus 1), `test_dry_run_plan_claims_nothing`, `test_expired_lease_does_not_plan_while_a_run_is_in_flight` (Review Focus 3), `test_unpartitioned_table_has_one_whole_table_candidate` and `test_whole_table_policy_has_one_whole_table_candidate` (Review Focus 2), `test_manual_run_leaves_candidates_alone`, a replay test of an old history through the reconciliation workflow; run, see them fail.
- [ ] Implement; full backend suite, `ty`, `ruff`, `lint-imports`; commit `feat(table-maintenance): compact only the top N candidates of a table per run`.

### Task 7: the run moves its candidates on, and an out-of-memory retry takes fewer partitions

**Files:**
- Modify: `application/service/table_maintenance_run/submit_maintenance_operation.py` (first submit of a run → `start` its candidates), `record_table_maintenance_operation_result.py` (`finish` the run's candidates when `rewrite_data_files` ends: succeeded or finally failed; an attempt that will be retried changes nothing), `adapter/hybrid/temporal/inbound/workflows/table_maintenance_workflow.py` (after an `oom` attempt, the next attempt uses the next filter set), plan rendering in `plan_table_maintenance.py`
- Test: service tests, workflow tests (time-skipping harness), replay test

**Interfaces:**
- Produces: the plan's `rewrite_data_files` entry carries `filter_sets: list[list[{spec_id, where}]]` — index 0 = all selected partitions (equals `filters`), index 1 = the top half (ceil), index 2 = the top quarter (ceil), duplicates dropped, never empty. The workflow sends `filter_sets[min(oom_attempts_so_far, len - 1)]` as the attempt's filters under `workflow.patched("fewer-partitions-after-oom")`; old histories and plans without `filter_sets` keep `filters`. The candidates a smaller set leaves out stay claimed by the run and are finished with it (the next observation re-scores them).

- [ ] Tests first: `test_first_submit_starts_the_claimed_candidates`, `test_succeeded_compaction_marks_its_candidates_done`, `test_finally_failed_compaction_marks_its_candidates_failed`, `test_retried_attempt_leaves_candidates_running`, workflow `test_oom_retry_submits_the_top_half_of_the_partitions`, a replay test of a pre-milestone history; run, see them fail.
- [ ] Implement; commit `feat(table-maintenance): move candidates with their run and retry an out-of-memory compaction on fewer partitions`.

### Task 8: candidates API

**Files:**
- Create: `application/port/inbound/compaction_candidate/list_compaction_candidates/{input,output,use_case}.py`, `application/service/compaction_candidate/list_compaction_candidates.py`, `adapter/inbound/web/compaction_candidate/{router.py, dto.py, __init__.py}`
- Modify: `web_use_cases.py`, `register_routes.py`, `openapi.json` and the console client via `task dev:generate-api`
- Test: service and route tests, schema test

**Interfaces:**
- Produces: `GET /v1/tables/{table_uuid}/compaction-candidates` → `CompactionCandidatesApiResponse(partitions_per_run: int, candidates: list[CompactionCandidateApiResponse])`; each item: `partition: {spec_id, values}`, `partition_label: str` (`field=value` pairs from the table's specs, or `whole table`), `state`, `hold_reason`, `reducible_files`, `data_bytes`, `estimated_gb_hours`, `score`, `rank: int | None` (1-based among pending), `claimed_by_run_id`, `lease_expires_at`, `last_written_at`, `observed_at`. Sorted by score descending.

- [ ] Tests first (sorting, rank only for pending, label for an identity and a day transform, unknown table 404); implement; regenerate the client (a second run changes nothing); commit `feat(table-maintenance): list a table's compaction candidates`.

### Task 9: the console shows candidates and why one was not picked

**Files:**
- Create: `src/components/tabs/CandidatesTab.tsx` (+ test), `src/lib/candidateText.ts` (+ test)
- Modify: `src/pages/TablePage.tsx` (`TABS`: "Candidates" after "Maintenance", inside `MaintenanceGate`), `src/pages/TablePage.stories.tsx` / `storyData.ts`, `reconciliationText.ts` (labels for `all_held` / `all_claimed`)
- Test: unit tests, stories `Pages/Table` `Candidates`, `CandidatesEmpty`, `CandidatesPhone`

**Interfaces:**
- Produces: a `DataTable` (columns via `createDataTableColumnHelper`) with Partition (`font-mono`), Score, Removable files, Data, Est. GB·h (`tabular-nums`), State, and "Why not picked": held too small → "Too small to be worth compacting", held recently written → "Still being written; checked again after a quiet period", pending with rank > N → "Score below the top N (N per run)", claimed / running → "In run <run id>", done / failed → "Waiting for the next observation". Empty state: "No partition needs compaction." Status colours per `src/data-platform/frontend/CLAUDE.md` (held and pending neutral).

- [ ] Tests first; implement; console unit + story tests, `tsc`, `eslint`; commit `feat(console): show a table's compaction candidates and why each was not picked`.

### Task 10: settings and chart

**Files:**
- Modify: `bootstrap/configs/app_settings.py` (new nested `CompactionSettings`, env `GLAC_COMPACTION__*`), wiring in `build_use_cases.py` / `build_connected_use_cases.py`, `platform/25-lakehouse-control-plane/chart/values.yaml` + `templates/configmap.yaml`, `platform/25-lakehouse-control-plane/README.md`
- Test: `tests/bootstrap/configs/test_app_settings.py`, wiring test

**Interfaces:**
- Produces: `CompactionSettings`: `partitions_per_run: int = 10`, `min_partition_bytes: int = 0`, `quiet_seconds: int = 120`, `benefit_weight: float = 0.7`, `cost_weight: float = 0.3`, `benefit_reference_files: int = 100`, `cost_reference_gb_hours: float = 1.0`, `default_throughput_bytes_per_hour: int = 2147483648`, `size_s_max_bytes: int = 268435456`, `size_m_max_bytes: int = 1073741824`. Chart: `compaction:` block with the same keys in camelCase. Defaults must keep the e2e passing on its current timeouts (its tables are KB-sized: `min_partition_bytes` 0; `quiet_seconds` short enough that the regions scheduled compaction still lands well inside `RUN_TIMEOUT_SECONDS`). The reasons for both filter defaults go on KCL-54 as a comment.

- [ ] Tests first; implement; commit `feat(table-maintenance): make candidate selection and scoring configurable`. (Tasks 4–7 may take these values as plain parameters until this task wires them.)

### Task 11: incremental observation, bounded

**Files:**
- Create (if it lands): `application/domain/model/table/observation_cursor.py` (last processed snapshot id on `Table`), adapter support in `observation_mapper.py` / `read_table_metadata_pyiceberg_gateway.py` for "partitions changed since snapshot X" (ADDED entries of manifests added by later snapshots), fallback to a full scan when X has expired or is not an ancestor of the current snapshot
- Test: adapter tests over a real PyIceberg in-memory / SQL catalog, sync tests

**Interfaces:**
- Produces (if it lands): reconcile re-scores only candidates of changed partitions plus held ones whose quiet period ended; the full scan stays the path for health and for the fallback. Decide in the task: whether compaction's own snapshots (operation `replace`) count as changes (they must, so a compacted partition is re-observed and leaves the candidates), and how delete-file-only snapshots count.
- Stop rule: if after the tests for expired snapshots, compaction snapshots and delete files any case is not clean, revert this task's code, keep the full scan, and post on KCL-53 what failed and the risk "large tables are slow to observe". Either outcome is DONE for this task.

- [ ] Tests first; implement or stop per the rule; commit `feat(table-maintenance): observe only partitions changed since the last processed snapshot` (or no commit plus the KCL-53 comment).

### Task 12: documentation

- [ ] `platform/25-lakehouse-control-plane/README.md` ("Compaction candidates": what a candidate is, states, filters, score, top N, settings); `src/data-platform/backend/CLAUDE.md` (the new aggregate in the context's aggregate list); `docs/agents/project-history.md` one line; `docs/agents/known-follow-ups.md` the risks. `uv run pre-commit run shared --all-files` passes. Commit `docs(table-maintenance): record partition candidates and scoring`.

---

## Verification on the cluster (main session, after review)

**Deploy size: small** (wave 25 only: images, chart values, ConfigMap keys; the new SQL table is created by the migrate Job's `create_schema`). Redeploy with `build.sh` + `bootstrap.sh`, run the e2e once (regression: the regions scheduled compaction now goes through candidates).

1. **Top N.** Create `iceberg.e2e.tm_cand_events (id bigint, day date, payload varchar) WITH (partitioning = ARRAY['day'])`, insert 6 days × 6 single-row inserts (one file each). Include it with a discovery rule, attach a copy of the platform default policy with `reducible_files.at_least: 3` and a short cooldown. Set `compaction.partitionsPerRun: 2` in `values.yaml` and redeploy (restore afterwards with `git restore`, never `kubectl patch configmap`). After `quiet_seconds`: `GET /v1/tables/<uuid>/compaction-candidates` lists 6 pending with scores; the scheduled run's Temporal input (`.plan.operations[].filters[].where`) names exactly the two best days; during the run those two are `claimed` / `running`, after it `done` and then removed on the next observation, while the other four stay `pending` with rank 1–4; the next round takes the next two.
2. **Filters.** Insert into one day again: it is `held` / `recently_written` and leaves the hold after the quiet period. Set `minPartitionBytes` above one partition's size: that partition is `held` / `too_small`.
3. **Cost from history.** After a few runs, a candidate's `estimated_gb_hours` uses the measured throughput (compare with `default_throughput_bytes_per_hour`).
4. **Console.** The Candidates tab lists the partitions sorted by score with the "Why not picked" text; screenshot.
5. **Less work after OOM** is covered by the workflow test; forcing it on the cluster needs the milestone 2 crafted table split into partitions — try it only if cheap, else write the risk on KCL-50.
6. **Clean up** the test table, rule and policy; restore `values.yaml` and redeploy.

**E2e decision for the main session:** worth adding: the regions scheduled run's candidates endpoint returns no `failed` candidate and the Candidates endpoint answers for both tables. The top-N scenario needs its own table and a lowered N (a cluster-wide setting), so it stays out of the e2e.
