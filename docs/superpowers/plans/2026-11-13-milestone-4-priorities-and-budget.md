# Milestone 4: Priorities and Budget Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One global scheduler decides, round by round, which tables' compaction candidates run, ranked by score × priority within a GB·hour budget; policies carry P0 / P1 / P2 with an SLA; the console shows each round and the overdue candidates.

**Architecture:** Reconcile keeps observing and scoring candidates (milestone 3), but a due compaction no longer claims candidates by itself: candidates of a due table are `pending`, and a not-due table's are `held` / `not_due`. A Temporal Schedule starts `CompactionRoundWorkflow` every round. Its activity ranks every pending candidate across tables by `score × priority weight`, takes them in order until the round's GB·hour budget is used (at most `partitions_per_run` per table), marks them `granted` under a lease, saves a `CompactionRound` record, and returns the granted tables. The workflow then signals each table's reconciliation workflow (`compaction_granted`), which plans as usual and claims only its granted candidates. The per-table workflow still dispatches, so one operation per table holds. Candidate rows get an optimistic `version`, because the scheduler and the reconcile now both write them.

**Tech Stack:** Python 3.13, Pydantic domain models, SQLAlchemy Core, Temporal Python SDK (workflows, schedules, signals), FastAPI, React + TanStack Query + Orval client, Helm chart wave 25.

**Spec:** `docs/superpowers/specs/2026-11-13-table-health-roadmap-design.md` (section "4. Priorities and budget"); Linear KCL-58, KCL-59, KCL-60 (read them: they add the SLA per priority and the overdue mark).

## Global Constraints

- The scheduler governs `rewrite_data_files` only. `expire_snapshots`, `rewrite_manifests`, `remove_orphan_files` keep running on the reconcile's own trigger conditions and use no budget.
- Never two maintenance operations on one table at the same time: only the table's reconciliation workflow starts runs (ADR 0002).
- A manual run is unchanged: it compacts the whole table, uses no budget and leaves the candidates alone.
- `priority` lives on the maintenance policy content, values `P0` / `P1` / `P2`, default `P2`; a policy without the field reads as `P2` (policy versions already stored have no field).
- Defaults (settings `GLAC_SCHEDULER__*`, chart block `scheduler:`): `round_seconds` 120, `budget_gb_hours` 0.05, `priority_weights` P0 4 / P1 2 / P2 1, `sla_seconds` P0 3600 / P1 14400 / P2 28800, `grant_lease_seconds` 600, `rounds_kept` 500.
- Every workflow change that alters the command sequence of a running workflow goes behind `workflow.patched`. Adding a signal handler and a wake reason does not.
- Project rules: one object per file, `from __future__ import annotations`, StrEnum, ABC ports, DDD layering (lint-imports), TDD, every commit passes `pytest`, `ty check`, `ruff check .`, `ruff format --check`, `lint-imports`, and the console's `npm run test`, `test:stories`, `tsc`, `eslint`.
- No new dependencies. Never `kubectl patch configmap`. No explanatory comment blocks in `values.yaml`.
- Progress, decisions and blockers go to the Linear issue they concern (KCL-58, 59, 60) as comments in Traditional Chinese.

## Decisions taken by the main session (rulings)

- **Grant, then claim.** The scheduler does not claim for a run (it does not know the run id). It moves `pending` → `granted` (new state) with `granted_round_id` and `lease_expires_at = now + grant_lease_seconds`. The reconcile's plan moves its own `granted` → `claimed` for the run. A grant whose lease ended is `pending` again at the next observation (same rule as an expired claim).
- **Not due means held.** When the table's compaction is not due (cooldown, trigger not met, needs attention, operation disabled, dry run), its candidates are `held` with the new hold reason `not_due`, so the scheduler only sees work a run could start now. The small / recent filters still apply first (a too-small partition says `too_small`, not `not_due`).
- **Strict order.** The round walks the ranked list and stops at the first candidate that does not fit the remaining budget; the rest are skipped `budget_used`. The first candidate of a round is always taken even if it alone exceeds the budget, so a large partition is not starved. A table's candidates beyond `partitions_per_run` in one round are skipped `table_share_used`.
- **Rank** = `score × weight(priority)`, ties by the milestone 3 candidate rank (`CompactionCandidate.rank`). The SLA does not change the rank; it marks a candidate `overdue` when it has been pending longer than its priority's SLA (`pending_since`, set when a candidate becomes pending and kept while it stays pending or granted). Overdue is shown, not acted on (a candidate overdue for long is a sign the budget is too small).
- **Priority is stored on the candidate** at each observation (from the applicable policy), so the scheduler reads one table and does not resolve policies.
- **Version check.** `CompactionCandidate.version` (int, starts at 1, +1 on every save). The SQL repo's `save_all` runs in one transaction and updates `WHERE id = :id AND version = :expected`; any miss rolls back and raises `StaleCompactionCandidate`. Both callers run in Temporal activities whose retry re-reads. This closes the milestone 3 lost-update risk.
- **Schema evolution.** `create_schema` only creates missing tables, so existing `compaction_candidates` would miss the new columns. Add `add_missing_columns(engine)`: for every table in `metadata`, each column the database lacks is added with `ALTER TABLE ... ADD COLUMN`; a new column must be nullable or carry a `server_default`. Candidate rows are derived data, so no backfill is needed beyond the defaults.
- **Finding a round in the Temporal UI.** Register the KeywordList search attribute `GrantedTableUuids` in the Temporal wave's `bootstrap.sh` (beside `TableUuid`); the round workflow upserts the uuids it granted, so `GrantedTableUuids = "<uuid>"` finds every round that picked a table. The workflow's static summary says how many partitions of how many tables it granted.
- **One scheduler.** A Temporal Schedule `compaction-rounds` (overlap `SKIP`) starts `CompactionRoundWorkflow` every `round_seconds`; the worker ensures it at start, as it does the discovery schedules.

## Review Focus

1. A table whose run is in flight when its grant arrives: the signal wakes the workflow, which plans only after the run ends; the grant must still be claimable then (lease 600 s ≥ a typical run) and, if the lease ended, the candidates go back to pending, never stay `granted` forever.
2. A plan and a round writing the same candidate at once: one raises `StaleCompactionCandidate`, its activity retries, and no update is lost (test with two repos on one database).
3. A policy version stored before this milestone (no `priority`) reads as `P2` everywhere: plan, API, console editor.
4. A round with no pending candidates saves a round record with nothing picked and signals nobody; a round whose only candidate exceeds the budget still picks it.
5. The e2e regions table still gets its scheduled compaction (now through a round, at most `round_seconds` later) and the run's filter still names only its granted partitions.

---

### Task 1: Priority on the maintenance policy

**Files:**
- Create: `backend/context/table_maintenance/application/domain/model/table_maintenance_policy/maintenance_priority.py`
- Modify: `maintenance_policy_content.py` (field), the policy API DTOs (request / response, under `adapter/inbound/web/...maintenance_policies...`), `frontend/src/...` policy editor and policy version page, `openapi.json` + `task dev:generate-api`
- Test: domain tests beside the existing policy content tests; API tests; console editor tests and stories

**Interfaces:**
- Produces: `MaintenancePriority(StrEnum)` with `P0 = "P0"`, `P1 = "P1"`, `P2 = "P2"`; `MaintenancePolicyContent.priority: MaintenancePriority = MaintenancePriority.P2`; API field `priority` on policy create / update / read.

- [ ] Test: `test_policy_content_without_priority_reads_as_p2` — `MaintenancePolicyContent.from_primitives(<platform default primitives without "priority">).priority is MaintenancePriority.P2`.
- [ ] Test: `test_policy_content_round_trips_priority` — content with `priority="P0"` serialises to `"priority": "P0"` and back.
- [ ] Test: `test_platform_default_priority_is_p2`.
- [ ] API test: create a policy with `"priority": "P1"`, GET returns `"priority": "P1"`; a body without it returns `"P2"`; `"P3"` is 422.
- [ ] Implement, regenerate the client, add a Priority select (P0 / P1 / P2) to the policy editor and show it on the version page; console tests: the editor sends the chosen priority; a policy without it shows P2.
- [ ] Commit `feat(table-maintenance): give maintenance policies a priority` (backend) and `feat(console): edit a policy's priority` (console), or one commit if they cannot pass separately.

### Task 2: Add missing columns at schema creation

**Files:**
- Create: `backend/context/table_maintenance/adapter/outbound/shared/sql/add_missing_columns.py`
- Modify: `create_schema.py` (call it after `create_all`)
- Test: `tests/.../shared/sql/test_add_missing_columns.py`

**Interfaces:**
- Produces: `add_missing_columns(engine: Engine) -> list[str]` returning `"<table>.<column>"` for each column added.

- [ ] Test: `test_adds_a_column_the_database_lacks` — create a SQLite table `t(id)`, register `Table("t", metadata, Column("id"...), Column("extra", Integer, nullable=True))`, call it, assert `inspect(engine).get_columns("t")` names `extra` and the return value is `["t.extra"]`.
- [ ] Test: `test_adds_nothing_when_up_to_date` — returns `[]` on a fresh `create_all`.
- [ ] Test: `test_refuses_a_new_column_that_is_not_nullable_and_has_no_default` — raises `ValueError` naming the column.
- [ ] Implement with `sqlalchemy.inspect`, compile the column type with the engine's dialect, include `DEFAULT <server_default>` when present. Log each added column.
- [ ] Commit `feat(table-maintenance): add missing columns when the schema is created`.

### Task 3: Candidate version, priority, grant and not-due hold

**Files:**
- Create: `compaction_candidate/stale_compaction_candidate.py`
- Modify: `compaction_candidate.py`, `candidate_state.py` (add `GRANTED = "granted"`; `holds_a_claim` stays claimed / running; add `holds_a_lease` = granted / claimed / running), `hold_reason.py` (add `NOT_DUE = "not_due"`), `candidate_score.py` or the aggregate (`priority`), the SQL table (`version` Integer `server_default="1"`, `priority` String `server_default="P2"`, `granted_round_id` String nullable, `pending_since` UtcDateTime nullable), row mapper, `compaction_candidates_sql_repo.py`, the outbound port (`list_pending()` across tables)
- Test: aggregate tests, SQL repo tests (SQLite)

**Interfaces:**
- Produces:
  - `CompactionCandidate.version: int = 1`, `.priority: MaintenancePriority`, `.granted_round_id: str | None`, `.pending_since: datetime | None`
  - `CompactionCandidate.grant(round_id: str, lease_until: datetime, now: datetime) -> None` (pending only, else `InvalidCandidateTransition`)
  - `CompactionCandidate.claim(run_id, lease_until, now)` now requires `GRANTED` and keeps `granted_round_id`, so the console can say which round granted the run's partitions.
  - `CompactionCandidate.observe(..., priority: MaintenancePriority, ...)`: a granted candidate with a live lease keeps its grant (like a claim); an expired grant is pending again; `pending_since` is set when it becomes pending and kept while pending or granted; cleared when held, claimed or finished.
  - `CompactionCandidate.overdue(sla: Mapping[MaintenancePriority, timedelta], now) -> bool`
  - `CompactionCandidatesRepo.list_pending() -> list[CompactionCandidate]` (every table)
  - `StaleCompactionCandidate(Exception)` raised by `save_all` when a row's version moved.

- [ ] Tests (aggregate): `test_grant_moves_pending_to_granted_with_a_lease`, `test_grant_refuses_a_held_candidate`, `test_claim_needs_a_grant`, `test_observation_keeps_a_live_grant`, `test_observation_returns_an_expired_grant_to_pending`, `test_pending_since_survives_a_grant_and_clears_on_claim`, `test_overdue_after_the_priority_sla` (P2 pending 8 h + 1 s is overdue, P0 pending 59 min is not).
- [ ] Tests (repo): `test_save_increments_the_version`, `test_save_of_a_stale_candidate_raises_and_saves_nothing` (two repos on one SQLite file: both load, A saves, B's `save_all([b1, b2])` raises `StaleCompactionCandidate` and b2 is not written), `test_list_pending_reads_every_table`, `test_reads_rows_written_before_the_new_columns` (row inserted without the new columns reads as version 1, P2).
- [ ] Implement. Commit `feat(table-maintenance): version, priority and grants on compaction candidates`.

### Task 4: Reconcile claims only granted candidates

**Files:**
- Modify: `pick_compaction_candidates.py`, `select_top_candidates.py` / `candidate_shortfall.py` (new shortfall `awaiting_schedule`), `plan_table_maintenance.py`, `sync_compaction_candidates.py` (pass priority and the not-due hold)
- Test: `test_plan_compaction_candidates.py`, domain service tests

**Interfaces:**
- Consumes: Task 3.
- Produces: verdict `awaiting_schedule` on the compaction check when it is due but the table holds no granted candidate; `CandidateShortfall.AWAITING_SCHEDULE`.

- [ ] Tests: `test_due_compaction_without_a_grant_starts_nothing_and_says_awaiting_schedule` (other due operations still planned); `test_due_compaction_claims_its_granted_candidates_only` (granted d1, d2 + pending d3 → run where names d1, d2; d3 stays pending); `test_granted_beyond_partitions_per_run_take_the_best` ; `test_not_due_compaction_holds_candidates_not_due` (cooldown → every candidate held `not_due`; too small stays `too_small`); `test_candidates_take_the_policy_priority` (policy P0 → candidates P0); `test_manual_run_leaves_grants_alone`; `test_a_stale_save_raises_for_the_activity_to_retry`.
- [ ] Implement; keep `release-unstarted-candidates` working for claimed candidates (a run that does not start hands its claims back to `pending`, not to `granted`).
- [ ] Commit `feat(table-maintenance): start compaction only on scheduler grants`.

### Task 5: Compaction round domain

**Files:**
- Create under `application/domain/model/compaction_round/`: `compaction_round.py` (aggregate), `compaction_round_id.py`, `round_pick.py`, `round_skip.py`, `skip_reason.py` (`budget_used`, `table_share_used`), `priority_weights.py`; under `application/domain/service/compaction_round/`: `plan_compaction_round.py`
- Test: domain tests

**Interfaces:**
- Produces:
  - `plan_compaction_round(candidates: Sequence[CompactionCandidate], *, weights: PriorityWeights, budget_gb_hours: float, partitions_per_run: int, sla: Mapping[MaintenancePriority, timedelta], now: datetime, skipped_kept: int = 20) -> CompactionRound`
  - `CompactionRound(id, started_at, budget_gb_hours, used_gb_hours, picks: tuple[RoundPick, ...], skips: tuple[RoundSkip, ...], skipped_total: int)`; `RoundPick` / `RoundSkip` carry `table_uuid`, `partition` (PartitionKey), `label`, `priority`, `score`, `weighted_score`, `estimated_gb_hours`, `overdue`; `RoundSkip.reason: SkipReason`; `CompactionRound.granted_tables() -> tuple[TableId, ...]` (in pick order, unique).
  - `PriorityWeights` value object (`weight(priority) -> float`, all > 0).

- [ ] Tests: `test_ranks_by_score_times_priority_weight` (P0 0.3 → 1.2 beats P2 0.9); `test_stops_at_the_first_candidate_over_the_budget` (0.02 + 0.02 fit 0.05, the next 0.02 is skipped `budget_used`, so are all after it even if smaller); `test_always_takes_the_first_candidate` (0.2 > budget 0.05 still picked, used 0.2); `test_caps_each_table_at_partitions_per_run` (third of one table skipped `table_share_used`, the walk continues); `test_keeps_the_first_skipped_and_counts_all` (`skipped_kept` 2 of 5 → 2 skips, `skipped_total` 5); `test_marks_overdue_candidates`; `test_empty_round`.
- [ ] Commit `feat(table-maintenance): plan a compaction round by score, priority and budget`.

### Task 6: Schedule a round (application service and storage)

**Files:**
- Create: inbound port `schedule_compaction_round` (use case, input, output), service `ScheduleCompactionRoundService`, outbound port `CompactionRoundsRepo` (`save`, `get`, `list_recent(limit, before)`, `purge(keep)`), SQL package `adapter/outbound/compaction_round/sql/` (table `compaction_rounds`, picks / skips as JSON), register it in `create_schema.AGGREGATE_SQL_PACKAGES`, wire it in the container
- Test: service and repo tests

**Interfaces:**
- Consumes: Tasks 3, 5.
- Produces: `ScheduleCompactionRoundUseCase.execute(input(now: datetime)) -> output(round_id: str, granted_table_uuids: list[str], picked: int, skipped_total: int, used_gb_hours: float)`. It loads `list_pending()`, plans the round, grants every pick (`grant(round_id, now + grant_lease, now)`) and saves them in one `save_all`, saves the round, purges rounds beyond `rounds_kept`. A `StaleCompactionCandidate` propagates (the activity retries the whole round; nothing was saved).

- [ ] Tests: `test_grants_the_picked_candidates_and_saves_the_round`; `test_leaves_skipped_candidates_pending`; `test_a_stale_candidate_saves_neither_grants_nor_round`; `test_purges_old_rounds`; repo round-trip of picks and skips.
- [ ] Commit `feat(table-maintenance): schedule compaction rounds`.

### Task 7: Round workflow, schedule and the reconcile's grant signal

**Files:**
- Create: contracts `adapter/hybrid/temporal/contracts/compaction_round/` (workflow name, input, schedule id, summary, activity names, search attribute key `GrantedTableUuids`), workflow `compaction_round_workflow.py`, activities `compaction_round_activities.py`, `ensure_compaction_round_schedule.py`; signal `TableReconciliationSignal.COMPACTION_GRANTED = "compaction_granted"`
- Modify: `table_reconciliation_workflow.py` (handler: `self._wake("compaction_granted", cancels_stop=True)`), the reconciliation record's known wake reasons, worker registration and start (`build_worker.py`), settings `SchedulerSettings` (`bootstrap/configs/scheduler_settings.py`, `AppSettings.scheduler`), chart `values.yaml` `scheduler:` block → ConfigMap `GLAC_SCHEDULER__*`, Temporal wave `platform/21-temporal/bootstrap.sh` (register `GrantedTableUuids` KeywordList; find where `TableUuid` is registered and do the same) and its `validate.sh` check
- Test: workflow tests (time-skipping env), schedule test, wire-name tests

**Interfaces:**
- Consumes: Task 6.
- Produces: workflow `CompactionRoundWorkflow`: run the schedule activity; upsert `GrantedTableUuids`; for each granted table signal `table-reconciliation:table-uuid=<uuid>` with `compaction_granted` through the existing signal activity (a missing workflow is logged and skipped, not a failure); return the activity's output.

- [ ] Tests: `test_round_signals_each_granted_table_once`; `test_round_with_nothing_granted_signals_nobody`; `test_a_missing_reconciliation_workflow_does_not_fail_the_round`; `test_reconciliation_plans_on_compaction_granted` (the plan activity is called with wake reasons `{compaction_granted: 1}`); `test_compaction_granted_wire_name`; `test_granted_table_uuids_search_attribute_name`; `test_ensure_schedule_is_idempotent` (mirror the discovery schedule test).
- [ ] Commit `feat(table-maintenance): run compaction rounds on a schedule and hand grants to tables`.

### Task 8: API

**Files:**
- Create: router `compaction_rounds` with `GET /v1/compaction-rounds?limit=&before=` (newest first) and `GET /v1/compaction-rounds/{round_id}`; DTOs `CompactionRoundApiResponse`, `CompactionRoundPickApiResponse`, `CompactionRoundSkipApiResponse`
- Modify: candidates DTO (`priority`, `granted_round_id`, `pending_since`, `overdue`), `openapi.json`, generated client
- Test: API tests

- [ ] Tests: list and get with picks / skips, 404 on unknown id, candidates response carries the new fields and `overdue` computed with the configured SLA.
- [ ] Commit `feat(table-maintenance): read compaction rounds through the API`.

### Task 9: Console

**Files:**
- Create: page `CompactionRoundsPage` at `/compaction-rounds` (nav item "Compaction rounds" after "Maintenance policies"), its stories; helper text for skip reasons
- Modify: `CandidatesTab.tsx` (Priority column; an "Overdue" notice badge; why-not-picked texts for `granted` "Granted in round <short id>", `held/not_due` "Compaction is not due on this table", pending "Waiting for the next round"), `lib/candidateText.ts`, router, nav
- Test: unit tests and stories (loaded, empty, error, phone width)

- [ ] The rounds page lists rounds newest first: when, budget, used (and percent), picked count, skipped count; a row expands to the picks (table linked to its Candidates tab, partition, priority, score, weighted score, GB·h, overdue) and the first skipped with their reason ("Budget used", "Table's share used"). Follow `src/data-platform/frontend/CLAUDE.md` (DataTable, semantic colours, notice only for overdue, `font-mono` for ids, `tabular-nums`).
- [ ] Commit `feat(console): show compaction rounds and overdue candidates`.

### Task 10: Docs and e2e hook

- [ ] `docs/agents/project-history.md` milestone 4 line; `src/data-platform/backend/CLAUDE.md` (new aggregate `CompactionRound`, the grant step), root `CLAUDE.md` Project Vision aggregate list; `platform/CLAUDE.md` wave 21–22 search attributes list; known-follow-ups: risks you could not close.
- [ ] Do not change `e2e.sh` (the main session decides).
- [ ] Commit `docs(table-maintenance): record priorities and budget scheduling`.

## Verification on the cluster (main session, after review)

**Deploy size: wave 21 bootstrap (search attribute) plus wave 25.** Run `KUBE_CONTEXT=retail-lakehouse bash platform/21-temporal/bootstrap.sh` (idempotent), then wave 25 `build.sh` + `bootstrap.sh`, then the e2e.

1. **Budget leaves work.** Two day-partitioned tables (`tm_sched_a` under a policy P0, `tm_sched_b` under P2, same shape: several days, 4+ files each, medium partitions so GB·h is visible), `budget_gb_hours` set so one round fits about two partitions, `round_seconds` 60. Rounds pick P0 partitions first, skip the rest `budget_used`; the next rounds pick the rest; every run's filter names only granted partitions; no table ever has two runs at once.
2. **Grant during a run.** A grant that arrives while the table runs another operation is claimed after it.
3. **SLA.** With `sla_seconds.P2` lowered to 120, a P2 candidate left by small budgets shows Overdue in the console and in the round.
4. **Temporal UI.** `GrantedTableUuids = "<uuid>"` lists the rounds that picked the table.
5. **Console.** Screenshot the rounds page (expanded) and the Candidates tab.
6. Restore `values.yaml` with `git restore`, redeploy, clean up tables, rules, policies.

**E2e decision for the main session:** suggested: after the regions scheduled run, a compaction round record lists a regions pick, and the reconciliation that started the run carries the `compaction_granted` wake reason.
