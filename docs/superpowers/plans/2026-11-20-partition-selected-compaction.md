# Partition-Selected Compaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Refreshed 2026-11-21 against HEAD `3da08480`** (KCL-91, KCL-96 and KCL-97 built since the plan was written at `bfdc0987`). What changed:
- KCL-96 deleted `get_table_health` (service, port, route and tests). Every step that changed the health service is gone, and only the plan service calls `assess_maintenance`.
- `PlanTableMaintenanceService` now takes a required `metrics_store` and saves the table's metrics on every observed plan. `plan_service_on_fakes` takes an optional `metrics_store`. Tasks 4 and 6 add `partition_selection` beside it.
- KCL-96's `measure_table` already uses `compute_reducible_files`, but keeps only the table's total. The assessment stays the only place that counts reducible files per partition, and no per-partition metric is added.
- Test helper names and fixtures now match HEAD:
  - the tables repo tests' `_table()`, `NOW` and `either_repo`;
  - the console's `op({...})` helper and its `≥` rule text;
  - the existing assess tests whose planned partition order changes.
- `test/fixtures.ts` and `PlatformSettingsPage.test.tsx` are out of Task 8 and Task 6: at HEAD they hold no run fixture and no four-group list.
- KCL-97's typed `PartitionTransform` lives in the catalog context. Table maintenance keeps its text transforms, so `build_partition_filters` is still unchanged.
- The cluster verification (Task 10) is batched with KCL-95. The rebuild running now covers KCL-91, KCL-96 and KCL-97.

**Goal:** With `per: partition`, a scheduled `rewrite_data_files` compacts only the partitions over `reducible_files.at_most`. A job takes at most N of them, those with the most reducible files first. A partition written within the quiet period waits, unless it has been over the target for longer than the maximum wait. Each run records the `where` clauses it passed, and the API and the console show them.

**Architecture:** Two pure domain functions do the selection:
- `track_over_target_partitions` keeps, for each partition over the target, the time it was first seen over it.
- `select_compaction_partitions` applies the quiet period, the maximum wait and the per-job cap.

`assess_maintenance` calls both. It plans the selected partitions, or reports the new verdict `waiting_for_writes` when every partition over the target is still being written, and it returns the updated over-target record. The plan service saves that record on the `Table` through a narrow repository write, and renders the `where` clauses with the existing `build_partition_filters`. The maintenance workflow passes those clauses to run creation, so every `OperationRun` keeps the `filters` its jobs were submitted with. Three platform settings (`GLAC_MAINTENANCE_COMPACTION_*`) shape the selection and appear on the Platform settings page.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK, Helm, React + TanStack Query + orval + MSW, Storybook/vitest.

**Spec:**
- Linear KCL-94 (https://linear.app/kcl10/issue/KCL-94) and its 2026-11-19 comment: the selection steps; "since when" lives on the table; a pure function, test-first; no halving after OOM.
- `docs/adr/0012-policies-on-the-catalog-hierarchy.md`, section "Compacting only the partitions that need it".
- What it builds on:
  - KCL-93 (plan `docs/superpowers/plans/2026-11-20-per-table-maintenance-workflow.md`): one workflow per table, whole-table compaction, no rounds, candidates or admission.
  - KCL-91 (plan `docs/superpowers/plans/2026-11-20-maintenance-policy-target-state.md`): `rewrite_data_files.target = {reducible_files: {at_most}, per}`, and cooldowns as platform settings. Its "Boundaries" section hands this plan partition selection, the three settings and the run's `where`.
  - KCL-96 (plan `docs/superpowers/plans/2026-11-20-overview-metric-trends.md`): `TableMetrics`, `measure_table` and `TableMetricsStore`, saved by the plan service.
  - KCL-97 (plan `docs/superpowers/plans/2026-11-20-schema-version-diff.md`): catalog context only. No file of this plan changes with it.
- **Read each file at HEAD before changing it; never apply a step against a remembered version.**

## Global Constraints

Decisions this plan makes are marked **(decided)** with the reason. The rest is copied from the issue, its comment and ADR 0012.

- **Over the target (KCL-91, unchanged):** a partition is over the target when its `compute_reducible_files(p, target_file_size)` is `> at_most`.
  - The target file size is the table's `write.target-file-size-bytes`, else 512 MiB (`resolve_target_file_size`).
  - Every partition of every spec in the observation is compared, including the partitions of an older spec, since the observation already lists them by `(spec_id, values)`.
  - **Reuse, not a second count (refresh).** `compute_reducible_files` is the function KCL-96's `measure_table` sums into the table's `reducible_files` metric. The assessment calls the same function per partition, as it does at HEAD. `TableMetrics`, the metrics store and the Prometheus export stay table-level: KCL-94 adds no per-partition metric (KCL-96 counts 17 series per table).
- **No scoring (KCL-89, KCL-94).** The only order is "most reducible files first", and it only decides which N partitions a capped job takes, as the issue says ("可減少檔案最多的先做"). There is no weighted score, no ranking across tables and no aging: KCL-89 dropped per-partition scoring.
- **Selection applies only to a scheduled plan with `per: partition` (decided).**
  - `per: table` compares the table's total and rewrites the whole table, with no `where`, no cap and no quiet period. The issue's comment says `per: table` "只比整張表，不帶 where", and the three settings are about choosing partitions.
  - A manual run of `rewrite_data_files` still compacts the whole table. A manual run assesses nothing, and it is the escape hatch a person uses.
- **Order and cap (issue, ADR):** the partitions allowed to run are sorted by reducible files, most first.
  - Ties go by `spec_id` ascending, then by `repr(values)` ascending **(decided: deterministic, so a retried plan picks the same set)**.
  - The job takes the first `partitions_per_job`. The rest stay over the target and are taken by a later check.
  - `PlannedOperation.partitions` holds the selection in this order. It is no longer the observation's order.
- **Quiet period and maximum wait (issue, decided in detail):** a partition over the target **waits** when all three of these hold:
  - its `last_written_at` is known;
  - `now - last_written_at < quiet_period`;
  - `now - over_target_since < max_quiet_wait`.

  Otherwise it is allowed to run.
  - When `last_written_at` is unknown (its snapshot has expired), the partition counts as quiet.
  - A `last_written_at` in the future (clock skew) makes the partition wait, bounded by the maximum wait.
  - A `quiet_period` or `max_quiet_wait` of `0` means nothing ever waits.
- **"Over the target since" lives on the table (comment):** `Table.over_target_partitions: tuple[OverTargetPartition, ...]` records each partition now over the target with `since`, the time the first plan saw it over. A partition no longer over the target is dropped from it. There is no separate SQL table.
  - **When the record is replaced (decided).** Every scheduled plan of a managed, observed table replaces the record with the assessment's. That includes a dry run, a compaction in cooldown and one needing attention, since being over the target does not depend on them. A policy with no `rewrite_data_files` block, or one with `per: table`, empties the record.
  - **When it is left alone (refresh: the health read is gone).** A manual plan and a skip do not touch it.
  - **Order in the plan (refresh).** The order is:
    1. `_record_last_commit`;
    2. `_save_metrics`;
    3. `_lift_stale_marks`;
    4. the assessment;
    5. the over-target record;
    6. the dry-run check.

    A metrics failure stays a warning and never stops the record.
- **The record has its own write (decided: mirrors `record_last_commit`, so a plan holding an old copy of the table never puts back state another writer stored since, and a lost race costs only a later `since`).**
  - `TablesRepo.record_over_target_partitions(table_id, partitions) -> bool` writes only the column `over_target_partitions_json`, and never once the table is dropped.
  - `TablesRepo.update` never writes that column.
  - Recording it does not move `updated_at`.
- **New verdict `waiting_for_writes` (decided: `RecordTableReconciliationService` refuses a due verdict without a run, and "not needed" would contradict the met measurement).** When at least one partition is over the target and every one of them waits:
  - `OperationVerdict.WAITING_FOR_WRITES = "waiting_for_writes"`;
  - the plan check verdict is `"waiting_for_writes"`;
  - `OperationResult.WAITING_FOR_WRITES = "waiting_for_writes"`;
  - `next_eligible_at` is the earliest time a waiting partition is allowed to run (`min(last_written_at + quiet_period, since + max_quiet_wait)`).

  Needs-attention and cooldown still take precedence and replace the verdict and `next_eligible_at`, exactly as they do today.
- **Measurements (decided).** With `per: partition`, two context counts (no threshold, unit `count`) follow `qualifying_partitions`: `selected_partitions` (in the planned job) and `waiting_partitions`. The key names `reducible_files`, `target_file_size` and `qualifying_partitions` do not change.
- **`where` rendering:**
  - **Rendering (ADR):** `build_partition_filters(table.name.catalog, observation.specs, selected)` gives one `SpecFilter` per spec. Each spec is one `where` and one `CALL`; `sql_builder.py` and `build_partition_filters` are not changed.
  - **Fallbacks (decided, the pre-KCL-93 rule R40).** A `ValueError` from the builder (a nanosecond type, an unsupported transform) compacts the whole table and logs a warning. If the selection holds a partition of an unpartitioned spec, or any rendered `where` is empty, the whole table is compacted and the plan's `filters` is `()`. So the recorded filters are always exactly what the jobs ran with.
- **Settings (issue, names decided):**

  | Setting | Env var | Default | Range | Chart key |
  |---|---|---|---|---|
  | Partitions per job | `GLAC_MAINTENANCE_COMPACTION_PARTITIONS_PER_JOB` | `10` | `1` to `1000` | `worker.compactionPartitionsPerJob` |
  | Quiet period | `GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS` | `120` | `≥ 0` | `worker.compactionQuietSeconds` |
  | Longest wait for quiet | `GLAC_MAINTENANCE_COMPACTION_MAX_QUIET_WAIT_SECONDS` | `3600` | `≥ 0` | `worker.compactionMaxQuietWaitSeconds` |

  - The ceiling of 1000 is decided: it bounds the size of one `where`.
  - The quiet period of 120 s is the old candidate default, "a few minutes" in the ADR.
  - The ConfigMap gives these settings to the api and the worker alike.
- **Platform settings page (decided):** a fifth group, key `partition_selection`, title "Compaction partition selection", placed between `cooldown_and_backoff` and `discovery`. At HEAD the groups are `execution_capacity`, `compute_sizes`, `cooldown_and_backoff`, `discovery`. Its items, in this order:

  | Key | Label | Unit | Description |
  |---|---|---|---|
  | `maintenance_compaction_partitions_per_job` | "Partitions per job" | `partitions` | "The most partitions one rewrite data files job compacts; those with the most reducible files go first, the rest wait for a later check." |
  | `maintenance_compaction_quiet_seconds` | "Quiet period" | `seconds` | "A partition written more recently than this waits for a later check, so compaction does not race its writers." |
  | `maintenance_compaction_max_quiet_wait_seconds` | "Longest wait for quiet" | `seconds` | "A partition over its target for this long is compacted even while it is still being written." |
- **The run records its `where` (issue: until KCL-95 changes the run model, it is kept on today's operation record).**
  - **Model.** `OperationRun.filters: tuple[SpecFilter, ...] = ()` holds the clauses every attempt of the operation is submitted with; `()` means the whole table. It is set when the run is created, from the plan. Only `rewrite_data_files` may hold filters: any other operation is refused with `InvalidRunTransition`.
  - **API.** Each operation of `GET /v1/table-maintenance-runs/{run_id}` and `GET /v1/tables/{table_uuid}/table-maintenance-runs` carries `filters: [{"spec_id": int, "where": str}]`.
- **No other change to execution (KCL-93 comment):** no halving of the partitions after an out-of-memory failure, since the size escalation S/M/L handles it. Size escalation, the result callback and `procedure_args` are unchanged.
- **No extra wake (decided: the issue says waiting partitions are "這次先跳過", skipped this time).** A waiting or left-over partition is taken by the next check that `on:` and the cooldown allow. The reconciliation gets no recheck timer. This is listed in known-follow-ups.
- **No data migration and no new `workflow.patched` markers.** A missing `over_target_partitions_json`, or a stored operation without `filters`, reads as `()`. The cluster is rebuilt before deploy (`task offboard`, `task onboard KUBE_CONTEXT=retail-lakehouse`), batched with KCL-95.
- **Boundary with KCL-95 (state it, do not build it):** KCL-95 makes a run one operation and moves the Maintenance, Reconciliations and Commits tabs to side panels.
  - Here the run model, its status rules, the callback route and the tab layouts stay as they are.
  - `filters` is one more field on today's `OperationRun`. KCL-95 moves it onto the single-operation run with the other procedure arguments.
  - The Maintenance tab gets one "Scope" line per compaction, which KCL-95 moves into its panel.
- Follow `CLAUDE.md` and the backend's own `CLAUDE.md`:
  - TDD; one object per file; `from __future__ import annotations`; StrEnum; ABC ports.
  - The domain imports only stdlib, `base` and Pydantic. Adapters reach domain types only through port re-exports: the tables row mapper imports `OverTargetPartition` from `port.outbound.table`, and the runs row mapper imports `SpecFilter` from `port.outbound.table_maintenance_run`.
  - Shell and tooling: `uv run`, never bare `python` / `pytest`; never `cd`; kubectl verb first, then flags; never `--no-verify`; never `sops`; never edit `.claude/settings*.json`.
  - Off limits: do not touch `platform/30-thanos`, `platform/24-e2e-validation`, the ArgoCD path or `.claude/worktrees/`; no comments in `values.yaml`.
- `<pytest>` below means `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`. `<vitest>` means `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run`. Never run two suites at once.
- Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=<backend|frontend|all>`.
  - A commit that changes `openapi.json` regenerates the client with `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`, commits it with the backend change and runs `scope=all`.
  - `git add` names explicit paths.
  - Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- **JSON round trip (Tasks 1 and 2).** A tracked partition's values must survive a store and load: an int, a float `1.5`, a bool, a `None` value and a string with a quote. The loaded entry must still match the observed partition, so its `since` is kept and not restarted on every plan.
- **Spec evolution (Tasks 1 and 4).** A table whose spec evolved keeps spec 0 and spec 1 partitions with equal values as two entries. A selection across both specs gives two filters, so two `CALL`s in one job.
- **Clock skew (Task 1).** A `last_written_at` later than `now` makes the partition wait. It is compacted once it has been over the target for `max_quiet_wait`, never held forever.
- **Unrenderable partition (Task 4).** A selected partition the builder cannot render (a `timestamp_ns` day partition) compacts the whole table. The run's `filters` is then `[]`, matching what Spark ran, not the unrendered selection.
- **Races (Tasks 2 and 4).** A plan that races a result record or a rename loses neither. The over-target record is written only by its narrow write, and `update` of an older copy keeps the stored record.
- **The plan order of KCL-96 (Task 4).** The metrics are saved before the assessment, and the over-target record after it. A metrics save or measure failure still leaves the record written. A skip forgets the metrics but leaves the over-target record as stored.
- **One count, two readers (Task 3).** The assessment's per-partition reducible files and the Overview's `reducible_files` card come from the same `compute_reducible_files` and the same target size. Nothing per-partition reaches `TableMetrics` or `/v1/table-metrics`.
- **Order is a tie-broken sort, not a score (Tasks 1 and 3).** The two existing tests that asserted observation order for `planned.partitions` now assert the selection order. No other test depends on the old order.

---

## File Structure

Paths and abbreviations:
- Backend paths are relative to `src/data-platform/backend/`.
- `TM` = `context/table_maintenance`; `TEMPORAL` = `TM/adapter/hybrid/temporal`.
- Tests mirror under `tests/`.
- Frontend paths are relative to `src/data-platform/frontend/src/`.

| File | Responsibility |
|---|---|
| `TM/application/domain/model/shared/{over_target_partition,partition_selection}.py` (new) | a tracked partition; the result of a selection |
| `TM/application/domain/model/table/{partition_selection_settings,default_partition_selection_settings}.py` (new) | cap, quiet period, maximum wait |
| `TM/application/domain/service/table/{track_over_target_partitions,select_compaction_partitions}.py` (new) | the two pure functions |
| `TM/application/domain/model/table/table.py`, `TM/application/port/outbound/table/tables_repo.py`, `TM/adapter/outbound/table/sql/{tables_table,table_row_mapper,tables_sql_repo}.py`, `tests/.../fakes/in_memory_tables_repo.py` | the table keeps its over-target partitions |
| `TM/application/domain/model/shared/{operation_verdict,maintenance_assessment,operation_assessment}.py`, `TM/application/domain/service/table/assess_maintenance.py` | selection in the assessment |
| `TM/application/service/table/plan_table_maintenance.py`, `tests/.../fakes/plan_service_on_fakes.py` | `where` clauses, record written, settings in |
| `TM/application/domain/model/table_reconciliation/operation_result.py`, `TM/application/service/table_reconciliation/record_table_reconciliation.py` | `waiting_for_writes` recorded |
| `bootstrap/configs/app_settings.py`, `bootstrap/container/{build_partition_selection_settings (new),build_platform_settings,build_use_cases,build_connected_use_cases}.py`, `TM/application/domain/model/shared/platform_settings.py`, `TM/application/service/table_maintenance_run/get_platform_settings.py` | settings and the page group |
| `TM/application/domain/model/table_maintenance_run/{operation_run,table_maintenance_run}.py`, the `create_table_maintenance_run` port and service, `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`, the runs row mapper, `table_maintenance_run_output_fields.py`, `TM/adapter/inbound/web/table_maintenance_run/dto.py` | the run records its `where` |
| `components/tabs/reconciliationText.ts`, `lib/compactionScopeText.ts` (new), `components/tabs/MaintenanceTab.tsx`, `stories/storyData.ts`, `pages/TablePage.stories.tsx` | console |
| `platform/25-lakehouse-control-plane/chart/{values.yaml,templates/configmap.yaml}`, `e2e.sh`, `README.md` | chart, e2e, docs |

---

### Task 1: The two selection functions

New files only.

**Files:**
- Create:
  - `TM/application/domain/model/shared/over_target_partition.py` and `TM/application/domain/model/shared/partition_selection.py`, exported from `TM/application/domain/model/shared/__init__.py`;
  - `TM/application/domain/model/table/partition_selection_settings.py` and `TM/application/domain/model/table/default_partition_selection_settings.py`, exported from `TM/application/domain/model/table/__init__.py` (`default_operation_cooldowns.py` is the pattern);
  - `TM/application/domain/service/table/track_over_target_partitions.py` and `TM/application/domain/service/table/select_compaction_partitions.py`, exported from `TM/application/domain/service/table/__init__.py`.
- Test (all new):
  - `tests/context/table_maintenance/application/domain/model/table/test_partition_selection_settings.py`;
  - `tests/context/table_maintenance/application/domain/service/table/test_track_over_target_partitions.py`;
  - `tests/context/table_maintenance/application/domain/service/table/test_select_compaction_partitions.py`.

**Interfaces:**
- Consumes (at HEAD):
  - `PartitionStats` (`spec_id`, `values: tuple[str | int | float | bool | None, ...]`, `last_written_at: datetime | None`);
  - `NonNegativeDuration` from the `shared` model;
  - `ValueObject` and `InvariantViolation` from `base`.
- Produces (all `ValueObject`):
  - `OverTargetPartition(spec_id: int, values: tuple[str | int | float | bool | None, ...], since: datetime)` with `is_of(partition: PartitionStats) -> bool` (equal `spec_id` and `values`).
  - `PartitionSelectionSettings(partitions_per_job: int, quiet_period: NonNegativeDuration, max_quiet_wait: NonNegativeDuration)`.
    - `partitions_per_job` is from 1 to 1000, else `InvariantViolation` "must be between 1 and 1000".
    - `platform_default()` returns `10`, `timedelta(seconds=120)`, `timedelta(hours=1)`.
    - `DEFAULT_PARTITION_SELECTION_SETTINGS = PartitionSelectionSettings.platform_default()`.
  - `PartitionSelection(selected: tuple[PartitionStats, ...] = (), waiting: tuple[PartitionStats, ...] = (), waiting_until: datetime | None = None)` with `@property all_waiting -> bool` (`waiting` non-empty and `selected` empty).
  - `track_over_target_partitions(previous: Sequence[OverTargetPartition], over_target: Sequence[PartitionStats], now: datetime) -> tuple[OverTargetPartition, ...]`.
    - It returns one entry per partition of `over_target`, in that order.
    - The entry keeps the previous `since` when it was tracked, else its `since` is `now`.
    - A previous entry not in `over_target` is dropped.
  - `select_compaction_partitions(over_target: Sequence[tuple[PartitionStats, int]], tracked: Sequence[OverTargetPartition], now: datetime, settings: PartitionSelectionSettings) -> PartitionSelection`.
    - Each pair is a partition over the target and its reducible files.
    - The waiting rule, the order and the cap are those of Global Constraints. `selected` is in that order, and `waiting` is in the same order.
    - `waiting_until` is the minimum of `min(last_written_at + quiet_period, since + max_quiet_wait)` over the waiting partitions, and `None` when none waits.
    - A partition missing from `tracked` counts as `since = now`.

- [ ] **Step 1: Write the failing tests**

```python
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)
SETTINGS = PartitionSelectionSettings.platform_default()

def p(spec_id, *values, written=None, files=10):
    return PartitionStats(spec_id=spec_id, values=values, data_file_count=files, position_delete_file_count=0,
                          equality_delete_file_count=0, total_data_file_size_bytes=0, last_written_at=written)

def since(partition, at):
    return OverTargetPartition(spec_id=partition.spec_id, values=partition.values, since=at)

# test_partition_selection_settings.py
def test_platform_default_selection_settings():
    s = PartitionSelectionSettings.platform_default()
    assert (s.partitions_per_job, s.quiet_period, s.max_quiet_wait) == (10, timedelta(minutes=2), timedelta(hours=1))
    assert DEFAULT_PARTITION_SELECTION_SETTINGS == s

@pytest.mark.parametrize("n", [0, 1001])
def test_partitions_per_job_out_of_range_is_refused(n):
    with pytest.raises(InvariantViolation, match="must be between 1 and 1000"):
        SETTINGS.with_changes(partitions_per_job=n)

def test_a_negative_quiet_period_is_refused():
    with pytest.raises(InvariantViolation):
        SETTINGS.with_changes(quiet_period=timedelta(seconds=-1))

# test_track_over_target_partitions.py
def test_a_new_partition_over_target_is_tracked_since_now():
    assert track_over_target_partitions((), [p(0, "eu")], NOW) == (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)

def test_a_tracked_partition_keeps_its_since():
    eu = p(0, "eu")
    assert track_over_target_partitions((since(eu, NOW - timedelta(hours=2)),), [eu], NOW) == (since(eu, NOW - timedelta(hours=2)),)

def test_a_partition_back_under_target_is_dropped():
    assert track_over_target_partitions((since(p(0, "eu"), NOW),), [], NOW) == ()

def test_the_same_values_in_two_specs_are_two_entries():
    old = since(p(0, "eu"), NOW - timedelta(hours=1))
    assert track_over_target_partitions((old,), [p(0, "eu"), p(1, "eu")], NOW) == (old, since(p(1, "eu"), NOW))

def test_a_round_tripped_entry_still_matches():
    observed = p(0, 1, 1.5, True, None, "o'neil")
    entry = track_over_target_partitions((), [observed], NOW)[0]
    assert OverTargetPartition.from_primitives(entry.to_primitives()).is_of(observed)

# test_select_compaction_partitions.py
def test_nothing_over_target_selects_nothing():
    assert select_compaction_partitions([], [], NOW, SETTINGS) == PartitionSelection()

def test_quiet_partitions_are_all_selected_under_the_cap():
    over = [(p(0, r), 5) for r in ("a", "b", "c")]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert (len(got.selected), got.waiting, got.waiting_until) == (3, (), None)

def test_the_cap_takes_the_most_reducible_first():
    over = [(p(0, f"r{i:02}"), i) for i in range(1, 13)]             # 12 partitions, reducible 1..12
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [s.values[0] for s in got.selected] == [f"r{i:02}" for i in range(12, 2, -1)]

def test_ties_break_by_spec_then_values():
    over = [(p(0, "b"), 5), (p(1, "a"), 5), (p(0, "a"), 5)]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [(s.spec_id, s.values) for s in got.selected] == [(0, ("a",)), (0, ("b",)), (1, ("a",))]

def test_a_recently_written_partition_waits():
    hot = p(0, "hot", written=NOW - timedelta(seconds=30))
    got = select_compaction_partitions([(hot, 5), (p(0, "cold"), 5)], [], NOW, SETTINGS)
    assert ([s.values for s in got.selected], [w.values for w in got.waiting]) == ([("cold",)], [("hot",)])
    assert got.waiting_until == NOW + timedelta(seconds=90)

def test_every_partition_waiting_is_all_waiting():
    hot = p(0, "hot", written=NOW - timedelta(seconds=30))
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS)
    assert (got.all_waiting, got.selected) == (True, ())

def test_a_partition_over_target_past_the_max_wait_runs_while_written():
    hot = p(0, "hot", written=NOW - timedelta(seconds=10))
    got = select_compaction_partitions([(hot, 5)], [since(hot, NOW - timedelta(minutes=61))], NOW, SETTINGS)
    assert (got.selected, got.waiting) == ((hot,), ())

def test_waiting_until_is_the_max_wait_when_it_comes_first():
    hot = p(0, "hot", written=NOW - timedelta(seconds=10))
    got = select_compaction_partitions([(hot, 5)], [since(hot, NOW - timedelta(minutes=59))], NOW, SETTINGS)
    assert got.waiting_until == NOW + timedelta(minutes=1)

def test_an_unknown_last_write_counts_as_quiet():
    got = select_compaction_partitions([(p(0, "eu", written=None), 5)], [], NOW, SETTINGS)
    assert (len(got.selected), got.waiting) == (1, ())

def test_a_future_last_write_waits_until_the_max_wait():
    skewed = p(0, "eu", written=NOW + timedelta(minutes=5))
    fresh = select_compaction_partitions([(skewed, 5)], [], NOW, SETTINGS)
    assert (fresh.all_waiting, fresh.waiting_until) == (True, NOW + timedelta(hours=1))
    old = select_compaction_partitions([(skewed, 5)], [since(skewed, NOW - timedelta(hours=1))], NOW, SETTINGS)
    assert old.selected == (skewed,)

def test_zero_quiet_period_never_waits():
    hot = p(0, "hot", written=NOW)
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS.with_changes(quiet_period=timedelta(0)))
    assert got.selected == (hot,)

def test_zero_max_wait_never_waits():
    hot = p(0, "hot", written=NOW)
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS.with_changes(max_quiet_wait=timedelta(0)))
    assert got.selected == (hot,)

def test_waiting_partitions_do_not_count_toward_the_cap():
    hot = [(p(0, f"h{i}", written=NOW), 50) for i in range(2)]
    quiet = [(p(0, f"q{i}"), 5) for i in range(3)]
    got = select_compaction_partitions(hot + quiet, [], NOW, SETTINGS.with_changes(partitions_per_job=2))
    assert ([s.values for s in got.selected], len(got.waiting)) == ([("q0",), ("q1",)], 2)

def test_partitions_of_two_specs_are_selected_together():
    got = select_compaction_partitions([(p(0, "eu"), 5), (p(1, "eu"), 7)], [], NOW, SETTINGS)
    assert [s.spec_id for s in got.selected] == [1, 0]
```

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/service/table/test_track_over_target_partitions.py tests/context/table_maintenance/application/domain/service/table/test_select_compaction_partitions.py tests/context/table_maintenance/application/domain/model/table/test_partition_selection_settings.py -v`. Expected: FAIL, the new names cannot be imported.
- [ ] **Step 3: Implement** the value objects and the two functions.
  - The bound on `partitions_per_job` is a `field_validator`.
  - `NonNegativeDuration` comes from the `shared` model, as `OperationCooldowns` uses it.
  - The tie key is `(-reducible, spec_id, repr(values))`.
- [ ] **Step 4: Run them and watch them pass.**
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): select the partitions over the target that a compaction job takes (KCL-94)`.

### Task 2: The table keeps its partitions over the target

**Files:**
- Modify:
  - `TM/application/domain/model/table/table.py`;
  - `TM/application/port/outbound/table/tables_repo.py`, and `TM/application/port/outbound/table/__init__.py` to re-export `OverTargetPartition`;
  - `TM/adapter/outbound/table/sql/tables_table.py`, `table_row_mapper.py` and `tables_sql_repo.py`;
  - `tests/context/table_maintenance/fakes/in_memory_tables_repo.py`.
- Test: `tests/context/table_maintenance/application/domain/model/table/test_table.py` (helpers `managed()`, `T0`), `tests/context/table_maintenance/adapter/outbound/table/test_tables_sql_repo.py` (helpers `_table()`, `NOW`, fixtures `repo`, `engine`, `either_repo`).

**Interfaces:**
- Consumes: `OverTargetPartition` (Task 1).
- Produces:
  - `Table.over_target_partitions: tuple[OverTargetPartition, ...] = ()`.
  - `Table.record_over_target_partitions(partitions: Sequence[OverTargetPartition]) -> bool` replaces the record and returns whether it changed. It returns `False` and changes nothing when the record is equal or the table is dropped, and it does not move `updated_at`.
  - `TablesRepo.record_over_target_partitions(table_id: TableId, partitions: Sequence[OverTargetPartition]) -> bool` (abstract). It writes only that column, where the status is not dropped, and returns whether a row was written. Its docstring follows `record_last_commit`'s.
  - Column `Column("over_target_partitions_json", JSON, nullable=True)`, holding `[{"spec_id", "values", "since"}]`, with `since` through `IsoDatetimeCodec` (`TM/adapter/outbound/shared/sql/iso_datetime_codec.py`).
    - `NULL` reads as `()`.
    - `TableRowMapper.to_values` leaves the key out, so `update` never writes it.
    - `TablesSqlRepo.create` writes `[]`.

- [ ] **Step 1: Write the failing tests**

```python
# test_table.py
EU = OverTargetPartition(spec_id=0, values=("eu",), since=T0)

def test_recording_over_target_partitions_replaces_them():
    table = managed()
    assert table.record_over_target_partitions((EU,)) is True
    assert table.over_target_partitions == (EU,)

def test_recording_the_same_partitions_changes_nothing():
    table = managed()
    table.record_over_target_partitions((EU,))
    assert table.record_over_target_partitions((EU,)) is False

def test_recording_does_not_move_updated_at():
    table = managed()
    before = table.updated_at
    table.record_over_target_partitions((EU,))
    assert table.updated_at == before

def test_a_dropped_table_records_nothing():
    table = managed()
    table.mark_dropped(T0 + timedelta(days=1))
    assert (table.record_over_target_partitions((EU,)), table.over_target_partitions) == (False, ())

# test_tables_sql_repo.py
def test_sql_round_trip_of_over_target_partitions(repo):
    repo.create(_table())
    entries = (OverTargetPartition(spec_id=0, values=("o'neil", 19700, 1.5, True, None), since=NOW),)
    assert repo.record_over_target_partitions(TableId("u1"), entries) is True
    assert repo.get(TableId("u1")).over_target_partitions == entries

def test_recording_over_target_partitions_twice_writes_once(either_repo):
    either_repo.create(_table())
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is True
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is False
    assert either_repo.get(TableId("u1")).over_target_partitions == entries

def test_update_keeps_the_stored_over_target_partitions(either_repo):
    either_repo.create(_table())
    stale = either_repo.get(TableId("u1"))
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    either_repo.record_over_target_partitions(TableId("u1"), entries)
    stale.rename(TableName(catalog="c", namespace="n", table="renamed"), NOW)
    either_repo.update(stale)
    assert either_repo.get(TableId("u1")).over_target_partitions == entries

def test_a_new_table_has_no_over_target_partitions(repo):
    repo.create(_table())
    assert repo.get(TableId("u1")).over_target_partitions == ()

def test_over_target_partitions_of_a_dropped_or_unknown_table_are_not_written(either_repo):
    either_repo.create(_table(status=TableStatus.DROPPED))
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is False
    assert either_repo.record_over_target_partitions(TableId("nope"), entries) is False
    assert either_repo.get(TableId("u1")).over_target_partitions == ()

def test_a_null_over_target_column_reads_as_none(repo, engine):
    repo.create(_table())
    with engine.begin() as connection:
        connection.execute(text("UPDATE tables SET over_target_partitions_json = NULL"))
    assert repo.get(TableId("u1")).over_target_partitions == ()
```

Add `record_over_target_partitions` to `InMemoryTablesRepo` with the same rules. Its `update` keeps the stored record (copy `over_target_partitions` from the stored table onto the one being saved). That also closes, for this field, the gap known-follow-ups names: "the fake does not follow the SQL adapter".

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table/test_table.py tests/context/table_maintenance/adapter/outbound/table/test_tables_sql_repo.py -k "over_target" -v`
- [ ] **Step 3: Implement.** The repo's `update` pops `over_target_partitions_json` from the values, as it already treats `last_committed_at`.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): keep a table's partitions over the compaction target and since when (KCL-94)`.

### Task 3: The assessment selects the partitions

**Files:**
- Modify:
  - `TM/application/domain/model/shared/operation_verdict.py`: add `WAITING_FOR_WRITES = "waiting_for_writes"`.
  - `TM/application/domain/model/shared/maintenance_assessment.py`: add `over_target_partitions: tuple[OverTargetPartition, ...] = ()`.
  - `TM/application/domain/model/shared/operation_assessment.py`: docstring only. `planned` is still set iff `DUE`, and `next_eligible_at` is also set for a waiting compaction.
  - `TM/application/domain/service/table/assess_maintenance.py`.
- Test: `tests/context/table_maintenance/application/domain/service/table/test_assess_maintenance.py` (helpers `table()`, `part(reducible, spec_id, value, size)`, `obs(...)`, `assess`, `compaction(...)`, `over`, `DAY_SPEC`, `NOW`), `test_assessment_plan.py` (helpers `part`, `obs`, `plan_of`, `compact_only`).

**Interfaces:**
- Consumes:
  - Task 1: both functions and `PartitionSelectionSettings`;
  - Task 2: `Table.over_target_partitions`;
  - at HEAD: `compute_reducible_files` and `resolve_target_file_size`, the same pair KCL-96's `measure_table` uses.
- Produces:
  - `assess_maintenance(table, policy, observation, now, *, cooldowns=DEFAULT_OPERATION_COOLDOWNS, partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS) -> MaintenanceAssessment`.
  - `_measure` passes `table`, `now` and `partition_selection` to `_measure_compaction(spec, observation, table, now, partition_selection)`. It returns `(assessment, planned, tracked)`; the other measures are unchanged.
  - With `per: partition`, `_measure_compaction` does these steps in order:
    1. It finds the qualifying partitions as today, with `[(p, compute_reducible_files(p, target)) …]`.
    2. It tracks them against `table.over_target_partitions`.
    3. It selects with `partition_selection`.
    4. It reports measurements in the order `reducible_files`, `target_file_size`, `qualifying_partitions`, `selected_partitions`, `waiting_partitions`.
    5. It plans `PlannedOperation(partitions=selection.selected)` when the selection is non-empty. That becomes a whole-table `PlannedOperation(operation)` when a selected partition belongs to an unpartitioned or unknown spec: the HEAD rule, now applied to the selection.
    6. When `selection.all_waiting`, the verdict is `WAITING_FOR_WRITES` with `next_eligible_at = selection.waiting_until`, and nothing is planned.
  - `_assess` sets `DUE` only when the measurement holds and the compaction is not all-waiting. Needs-attention and cooldown then override as today.
  - `MaintenanceAssessment.over_target_partitions` is the tracked tuple. It is `()` with `per: table`, with no `rewrite_data_files` block, or with nothing over the target.

- [ ] **Step 1: Write the failing tests** (in `test_assess_maintenance.py`; `written(part, at)` returns `part.with_changes(last_written_at=at)`)

```python
SELECTION = PartitionSelectionSettings.platform_default()

def _measurement(a, key):
    return next(m for m in a.measurements if m.key == key)

def _compaction_of(assessment):
    return next(o for o in assessment.operations if o.operation == Op.REWRITE_DATA_FILES)

def test_per_partition_plans_only_the_partitions_over_target():
    o = obs(partitions=(part(9, value=1), part(1, value=2), part(7, value=3)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.planned.partitions == (o.partitions[0], o.partitions[2])

def test_the_job_takes_at_most_the_cap():
    o = obs(partitions=tuple(part(6 + i, value=i) for i in range(12)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW, partition_selection=SELECTION))
    assert len(a.planned.partitions) == 10
    assert _measurement(a, "selected_partitions").observed == 10
    assert _measurement(a, "qualifying_partitions").observed == 12
    assert _measurement(a, "waiting_partitions").observed == 0

def test_all_partitions_under_target_is_not_due():
    result = assess_maintenance(table(), compaction(), obs(partitions=(part(3),)), NOW)
    a = _compaction_of(result)
    assert a.verdict == OperationVerdict.NOT_DUE
    assert (_measurement(a, "selected_partitions").observed, _measurement(a, "waiting_partitions").observed) == (0, 0)
    assert result.over_target_partitions == ()

def test_every_partition_being_written_waits():
    o = obs(partitions=tuple(written(part(9, value=v), NOW - timedelta(seconds=30)) for v in (1, 2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert (a.verdict, a.planned, a.next_eligible_at) == (OperationVerdict.WAITING_FOR_WRITES, None, NOW + timedelta(seconds=90))
    assert _measurement(a, "waiting_partitions").observed == 2

def test_some_waiting_some_selected_is_due():
    o = obs(partitions=(written(part(9, value=1), NOW - timedelta(seconds=30)), part(9, value=2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.verdict == OperationVerdict.DUE
    assert (_measurement(a, "selected_partitions").observed, _measurement(a, "waiting_partitions").observed) == (1, 1)

def test_a_partition_over_target_for_an_hour_runs_while_written():
    hot = written(part(9, value=1), NOW - timedelta(seconds=10))
    t = table()
    t.record_over_target_partitions((OverTargetPartition(spec_id=0, values=(1,), since=NOW - timedelta(minutes=61)),))
    a = _compaction_of(assess_maintenance(t, compaction(), obs(partitions=(hot,)), NOW))
    assert a.planned.partitions == (hot,)

def test_waiting_and_cooldown_reads_cooldown():
    t = table()
    t.record_operation_result(Op.REWRITE_DATA_FILES, True, NOW - timedelta(minutes=10))
    o = obs(partitions=(written(part(9), NOW - timedelta(seconds=30)),))
    a = _compaction_of(assess_maintenance(t, compaction(), o, NOW))
    assert (a.verdict, a.next_eligible_at) == (OperationVerdict.COOLDOWN, NOW - timedelta(minutes=10) + PLATFORM.rewrite_data_files)

def test_waiting_and_needs_attention_reads_needs_attention():
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    a = _compaction_of(assess_maintenance(t, compaction(), obs(partitions=(written(part(9), NOW),)), NOW))
    assert (a.verdict, a.planned) == (OperationVerdict.NEEDS_ATTENTION, None)

def test_the_assessment_returns_the_tracked_partitions():
    t = table()
    t.record_over_target_partitions((OverTargetPartition(spec_id=0, values=(3,), since=NOW - timedelta(hours=2)),))
    o = obs(partitions=(part(9, value=1), part(1, value=2), part(9, value=3)))
    assert assess_maintenance(t, compaction(), o, NOW).over_target_partitions == (
        OverTargetPartition(spec_id=0, values=(1,), since=NOW),
        OverTargetPartition(spec_id=0, values=(3,), since=NOW - timedelta(hours=2)),
    )

def test_tracking_continues_during_cooldown():
    t = table()
    t.record_operation_result(Op.REWRITE_DATA_FILES, True, NOW - timedelta(minutes=10))
    result = assess_maintenance(t, compaction(), obs(partitions=(part(9),)), NOW)
    assert _compaction_of(result).verdict == OperationVerdict.COOLDOWN
    assert len(result.over_target_partitions) == 1

def test_per_table_ignores_quiet_and_the_cap():
    o = obs(partitions=tuple(written(part(9, value=i), NOW) for i in range(12)))
    result = assess_maintenance(table(), compaction(per=CompactionUnit.TABLE), o, NOW)
    a = _compaction_of(result)
    assert (a.verdict, a.planned.partitions, result.over_target_partitions) == (OperationVerdict.DUE, (), ())

def test_no_compaction_block_tracks_nothing():
    policy = DEFAULT.with_changes(rewrite_data_files=None)
    assert assess_maintenance(table(), policy, obs(partitions=(part(9),)), NOW).over_target_partitions == ()

def test_partitions_of_an_older_spec_are_selected():
    month = PartitionSpecInfo(spec_id=1, fields=(PartitionFieldInfo(field_id=1001, name="m", source_column="ts",
                                                                     source_type="timestamp", transform="month"),))
    o = obs(specs=(DAY_SPEC, month), partitions=(part(9, value=1), part(8, spec_id=1, value=2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert {p.spec_id for p in a.planned.partitions} == {0, 1}

def test_a_selected_unpartitioned_partition_plans_the_whole_table():
    flat = PartitionSpecInfo(spec_id=1, fields=())
    o = obs(specs=(DAY_SPEC, flat), partitions=(part(9, value=1), PartitionStats(spec_id=1, values=(), data_file_count=9,
            position_delete_file_count=0, equality_delete_file_count=0, total_data_file_size_bytes=0)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert (a.verdict, a.planned.partitions) == (OperationVerdict.DUE, ())
```

`_needing_attention(op)` is the helper `test_needs_attention_wins_over_cooldown` already uses; do not write a new mark helper.

Existing tests whose assertion changes, and how:
- `test_assess_maintenance.py::test_per_partition_counts_the_partitions_over_target`:
  - the measurement tuple gains `Measurement(key="selected_partitions", observed=2, unit=MeasurementUnit.COUNT)` and `Measurement(key="waiting_partitions", observed=0, unit=MeasurementUnit.COUNT)`;
  - `planned.partitions == (o.partitions[2], o.partitions[0])` (9 before 7).
- `test_assessment_plan.py::test_partition_scope_selects_only_partitions_over_threshold`: `== (o.partitions[3], o.partitions[2])` (9 before 6).
- `test_assessment_plan.py::test_partitions_of_two_partitioned_specs_stay_partition_scoped`: unchanged. Both partitions have 6 reducible files, and the tie key puts spec 0 first, which is `o.partitions[:2]`.
- Every other test that compares a whole `per: partition` measurement tuple gains the two counts.

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/service/table -v`
- [ ] **Step 3: Implement**, then update the existing tests listed above.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q`. The plan service still ignores `planned.partitions` here, so its tests are unchanged.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): assess compaction on the partitions over the target, the cap and the quiet period (KCL-94)`.

### Task 4: The plan compacts the selected partitions and records what is over the target

**Files:**
- Modify:
  - `TM/application/service/table/plan_table_maintenance.py`;
  - `TM/application/domain/model/table_reconciliation/operation_result.py`: add `WAITING_FOR_WRITES = "waiting_for_writes"`, after `NEEDS_ATTENTION`;
  - `TM/application/service/table_reconciliation/record_table_reconciliation.py`: add `"waiting_for_writes": OperationResult.WAITING_FOR_WRITES` to `_RESULT_BY_VERDICT`;
  - `tests/context/table_maintenance/fakes/plan_service_on_fakes.py`: an optional keyword `partition_selection: PartitionSelectionSettings | None = None`, passed only when given, beside the existing optional `metrics_store`.
- Test:
  - `tests/context/table_maintenance/application/service/table/test_plan_table_maintenance_service.py` (helpers `_table`, `_partition`, `_field`, `_observe`, `_plan`, `_three_regions`, `_use_policy`, `_checks`, `_record`; fixtures `planner`, `tables_repo`, `catalog`, `policies`, `metrics_store`, `resolve_applicable_policy`, `now`);
  - `tests/context/table_maintenance/application/service/table_reconciliation/test_record_table_reconciliation_service.py`;
  - `tests/context/table_maintenance/adapter/outbound/table_reconciliation/test_table_reconciliations_sql_repo.py`.

**Interfaces:**
- Consumes:
  - Task 2: `Table.record_over_target_partitions` and `TablesRepo.record_over_target_partitions`;
  - Task 3;
  - at HEAD: `build_partition_filters` and `PlanTableMaintenanceUseCaseOutput.Filter(spec_id, where)`.
- Produces:
  - `PlanTableMaintenanceService(tables_repo, catalog_gateway, resolve_applicable_policy, *, metrics_store, cooldowns=DEFAULT_OPERATION_COOLDOWNS, partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS)`. It is kept as `self._partition_selection` and passed to `assess_maintenance`.
  - **Filters.** A planned `rewrite_data_files` with partitions gets `filters` from `build_partition_filters(table.name.catalog, observation.specs, planned.partitions)`. `_render` maps each `SpecFilter` to `PlanTableMaintenanceUseCaseOutput.Filter(spec_id, where)`, sorted by spec id.
    - The plan uses `()` when the builder raises `ValueError`, with the warning `"cannot scope rewrite_data_files of %s to partitions (%s); compacting the whole table"` through the module `logger`.
    - The plan also uses `()` when any `where` is `""`.
  - **The over-target record.** After a scheduled assessment, before the dry-run check, `table.record_over_target_partitions(assessment.over_target_partitions)` runs. When it reports a change, `self._tables_repo.record_over_target_partitions(table.id, ...)` follows. A manual plan and every skip leave it.
  - **The verdict.** `_VERDICTS[OperationVerdict.WAITING_FOR_WRITES] = "waiting_for_writes"`.
  - The docstring of `execute` replaces the paragraph that starts with "Every planned operation targets the whole table (no filters)". The new paragraph says that a scheduled plan with `per: partition` compacts the selected partitions with their `where` clauses, else the whole table; that a manual run compacts the whole table; and that a scheduled plan saves the partitions over the target.

- [ ] **Step 1: Write the failing tests** (extend `_partition(spec_id, values, files=10, size=10 * 1024, written=None)` so it adds `"last_written_at": written.isoformat()` when `written` is given)

```python
def test_due_compaction_targets_the_partitions_over_target(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, ["eu"]), _partition(0, ["us"], files=1), _partition(0, ["o'neil"])])
    compaction = _plan(planner, now).operations[0]
    assert compaction.filters == (
        PlanTableMaintenanceUseCaseOutput.Filter(spec_id=0, where="(`region` = 'eu') OR (`region` = 'o\\'neil')"),
    )
    assert compaction.procedure_args == {
        "options": {"target-file-size-bytes": 536870912, "min-input-files": 2, "partial-progress.enabled": True}
    }

def test_two_specs_give_two_filters(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now)                                             # spec 0 eu + spec 1 de, both 9 reducible
    assert [f.spec_id for f in _plan(planner, now).operations[0].filters] == [0, 1]

def test_the_plan_takes_at_most_the_cap(tables_repo, catalog, resolve_applicable_policy, now):
    planner = plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy,
                                    partition_selection=PartitionSelectionSettings.platform_default().with_changes(partitions_per_job=2))
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, [f"r{i}"], files=6 + i) for i in range(5)])
    assert _plan(planner, now).operations[0].filters[0].where == "(`region` = 'r3') OR (`region` = 'r4')"

def test_an_unrenderable_partition_compacts_the_whole_table(planner, tables_repo, catalog, caplog, now):
    _table(tables_repo, now)
    day_ns = {"field_id": 1000, "name": "d", "source_column": "ts", "source_type": "timestamp_ns", "transform": "day"}
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [day_ns]}], partitions=[_partition(0, [19700])])
    compaction = _plan(planner, now).operations[0]
    assert (compaction.operation, compaction.filters) == ("rewrite_data_files", ())
    assert "compacting the whole table" in caplog.text

def test_per_table_has_no_filters(planner, tables_repo, catalog, policies, now):
    _use_policy(policies, now, policy_with_operation(DEFAULT, OPS.REWRITE_DATA_FILES, RewriteDataFilesSpec(
        target=RewriteDataFilesTarget(reducible_files=AtMost(at_most=5), per=CompactionUnit.TABLE))))
    _table(tables_repo, now)
    _three_regions(catalog, now)
    assert _plan(planner, now).operations[0].filters == ()

def test_a_manual_compaction_has_no_filters(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _three_regions(catalog, now)
    assert _plan(planner, now, ["rewrite_data_files"]).operations[0].filters == ()

def test_every_partition_written_now_plans_no_compaction(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, ["eu"], written=now - timedelta(seconds=10))])
    plan = _plan(planner, now)
    assert "rewrite_data_files" not in [o.operation for o in plan.operations]
    check = _checks(plan)["rewrite_data_files"]
    assert (check.verdict, check.next_eligible_at) == ("waiting_for_writes", now + timedelta(seconds=110))

def test_the_plan_records_the_partitions_over_target(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, ["eu"]), _partition(0, ["o'neil"])])
    _plan(planner, now)
    assert tables_repo.get(TableId("u-1")).over_target_partitions == (
        OverTargetPartition(spec_id=0, values=("eu",), since=now),
        OverTargetPartition(spec_id=0, values=("o'neil",), since=now),
    )

def test_a_second_plan_keeps_since(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _three_regions(catalog, now)
    _plan(planner, now)
    _plan(planner, now + timedelta(minutes=10))
    assert {e.since for e in tables_repo.get(TableId("u-1")).over_target_partitions} == {now}

def test_a_dry_run_still_records_them(planner, tables_repo, catalog, policies, now):
    _use_policy(policies, now, DEFAULT.with_changes(dry_run=True))
    _table(tables_repo, now)
    _three_regions(catalog, now)
    _plan(planner, now)
    assert len(tables_repo.get(TableId("u-1")).over_target_partitions) == 3

def test_a_manual_plan_leaves_them(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _three_regions(catalog, now)
    _plan(planner, now, ["rewrite_data_files"])
    assert tables_repo.get(TableId("u-1")).over_target_partitions == ()

def test_a_metrics_failure_still_records_them(planner, tables_repo, catalog, metrics_store, monkeypatch, now):
    monkeypatch.setattr(metrics_store, "save", _database_down)
    _table(tables_repo, now)
    _three_regions(catalog, now)
    _plan(planner, now)
    assert len(tables_repo.get(TableId("u-1")).over_target_partitions) == 3

def test_a_stale_copy_does_not_overwrite_a_rename(planner, tables_repo, catalog, now):
    # rename the stored table from inside catalog.observe_table (the slow read), as
    # test_lifting_a_mark_keeps_a_change_made_while_the_catalog_was_read does
    ...  # → stored name is the new one, over_target_partitions has 3 entries

def test_the_plan_uses_the_injected_selection(tables_repo, catalog, resolve_applicable_policy, now):
    free = plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy,
                                 partition_selection=PartitionSelectionSettings.platform_default().with_changes(quiet_period=timedelta(0)))
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, ["eu"], written=now)])
    assert "rewrite_data_files" in [o.operation for o in _plan(free, now).operations]

def test_a_waiting_check_can_be_recorded(planner, tables_repo, catalog, now):
    # same table as test_every_partition_written_now_plans_no_compaction, then _record(plan, now)
    ...  # → the record's rewrite_data_files result is "waiting_for_writes"

# test_record_table_reconciliation_service.py
def test_waiting_for_writes_is_recorded(): ...   # check verdict "waiting_for_writes", next_eligible_at ISO string, no run_id
                                                # → OperationResult.WAITING_FOR_WRITES, next_eligible_at parsed to that datetime

# test_table_reconciliations_sql_repo.py
def test_a_waiting_for_writes_result_round_trips(): ...   # outcome with OperationResult.WAITING_FOR_WRITES → same after get
```

The four `...` bodies above copy the arrange part of the test named in their comment, so each states exactly the assertion after its arrow.

Replace `test_due_compaction_targets_the_whole_table` with `test_due_compaction_targets_the_partitions_over_target`, keeping its `procedure_args` assertion as shown. `test_plan_whole_table_compaction_has_no_filters` stays as it is, since its single spec is unpartitioned.

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/service tests/context/table_maintenance/adapter/outbound/table_reconciliation -k "filter or over_target or waiting or cap or since or selection or records_them or leaves_them" -v`
- [ ] **Step 3: Implement.** Use the R40 fallback shown above. `logger` is already module level in `plan_table_maintenance.py`.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q` with `tests/architecture`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): compact only the partitions over the target and record since when they are (KCL-94)`.

### Task 5: The console reads the new verdict and counts

**Files:**
- Modify: `components/tabs/reconciliationText.ts`, `components/tabs/reconciliationText.test.ts`, `stories/storyData.ts`. In `storyData.ts`, add two records to `RECONCILIATIONS` through its `reconciliation(...)` helper:
  - one whose `rewrite_data_files` result is `waiting_for_writes`;
  - one started compaction with `selected_partitions` 10 of `qualifying_partitions` 25 and `waiting_partitions` 3.
- Test: `reconciliationText.test.ts` (helpers `measurement`, `context`, `op({...})`, `REDUCIBLE_MET` with threshold 5 and comparison `">="`), the `ReconciliationsTab` stories.

**Interfaces:**
- Consumes: the record shapes of Task 4. The API types do not change (`result` and `key` are strings), so nothing is regenerated.
- Produces, as exact copy:
  - `RESULT_ORDER` gains `"waiting_for_writes"` right after `"needs_attention"`. `RESULT_LABELS.waiting_for_writes = "Waiting for writes"`.
  - `MEASUREMENT_LABELS.selected_partitions = "Selected partitions"`, `MEASUREMENT_LABELS.waiting_partitions = "Partitions being written"`.
  - `reasonSentence`, case `waiting_for_writes`: `` `Due: ${citeAll(met, op)}, but every partition over the target is still being written${when ? `; ${when}` : ""}.` ``, where `when = nextAllowed(op)`.
  - `reasonSentence`, cases `started` / `would_start` (not manual, `met` non-empty):
    - It starts with `Because ${citeAll(met, op)}.`.
    - When `selected_partitions` is present and less than `qualifying_partitions`, it adds `` ` This run compacts ${formatCount(selected)} of them` ``.
    - It then adds `` `; ${formatCount(waiting)} ${waiting === 1 ? "is" : "are"} still being written` `` when `waiting_partitions > 0`, and ends with `"."`.

- [ ] **Step 1: Write the failing tests**

```ts
it("says a compaction waits for writes", () => {
  const at = new Date(2026, 10, 20, 12, 5).toISOString();
  const measurements = [REDUCIBLE_MET, context("qualifying_partitions", 2)];
  expect(reasonSentence(op({ operation: "rewrite_data_files", result: "waiting_for_writes", measurements, next_eligible_at: at })))
    .toBe("Due: reducible files 1,240 across 2 partitions (needs ≥ 5 per partition), but every partition over the target is still being written; next allowed Nov 20, 12:05.");
});
it("says how many partitions a capped run compacts", () => {
  const measurements = [REDUCIBLE_MET, context("qualifying_partitions", 25), context("selected_partitions", 10), context("waiting_partitions", 3)];
  expect(reasonSentence(op({ operation: "rewrite_data_files", result: "started", measurements }))).toBe(
    "Because reducible files 1,240 across 25 partitions (needs ≥ 5 per partition). This run compacts 10 of them; 3 are still being written.");
});
it("says one partition is still being written", () => {
  const measurements = [REDUCIBLE_MET, context("qualifying_partitions", 2), context("selected_partitions", 1), context("waiting_partitions", 1)];
  expect(reasonSentence(op({ operation: "rewrite_data_files", result: "would_start", measurements }))).toBe(
    "Because reducible files 1,240 across 2 partitions (needs ≥ 5 per partition). This run compacts 1 of them; 1 is still being written.");
});
it("adds nothing when the run takes every partition over the target", () => {
  const measurements = [REDUCIBLE_MET, context("qualifying_partitions", 3), context("selected_partitions", 3), context("waiting_partitions", 0)];
  expect(reasonSentence(op({ operation: "rewrite_data_files", result: "started", measurements }))).toBe(
    "Because reducible files 1,240 across 3 partitions (needs ≥ 5 per partition).");
});
it("labels the new result and counts", () => {
  expect(resultLabel("waiting_for_writes")).toBe("Waiting for writes");
  expect(resultOrder("waiting_for_writes")).toBe(resultOrder("needs_attention") + 1);
  expect(measurementLabel("selected_partitions")).toBe("Selected partitions");
  expect(measurementLabel("waiting_partitions")).toBe("Partitions being written");
});
```

- [ ] **Step 2: Run and watch them fail:** `<vitest> reconciliationText`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** `<vitest>`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`; commit `feat(console): explain compaction waiting for writes and capped partition runs (KCL-94)`.

### Task 6: The three settings, their wiring and the Platform settings page

**Files:**
- Create: `bootstrap/container/build_partition_selection_settings.py` (export from `bootstrap/container/__init__.py`; `build_operation_cooldowns.py` is the pattern).
- Modify:
  - `bootstrap/configs/app_settings.py`;
  - `bootstrap/container/build_use_cases.py`, `build_connected_use_cases.py` and `build_platform_settings.py`;
  - `TM/application/domain/model/shared/platform_settings.py`;
  - `TM/application/service/table_maintenance_run/get_platform_settings.py`, including the `execute` docstring: "four groups" becomes "five groups";
  - `platform/25-lakehouse-control-plane/chart/values.yaml` and `chart/templates/configmap.yaml`;
  - `src/data-platform/frontend/src/stories/storyData.ts`: add the fifth group to `PLATFORM_SETTINGS`, whose comment already says "five groups". `PlatformSettingsPage.test.tsx` uses its own three-group fixture and does not change.
- Test:
  - `tests/bootstrap/configs/test_app_settings.py`;
  - new `tests/bootstrap/container/test_build_partition_selection_settings.py`;
  - `tests/bootstrap/container/test_build_platform_settings.py`, `test_build_use_cases.py` and `test_build_connected_use_cases.py`;
  - `tests/context/table_maintenance/application/service/table_maintenance_run/test_get_platform_settings.py`;
  - `tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run/test_platform_settings_route.py`.

**Interfaces:**
- Consumes: `PartitionSelectionSettings` and `DEFAULT_PARTITION_SELECTION_SETTINGS` (Task 1), the plan service kwarg (Task 4).
- Produces:
  - Three `AppSettings` fields:
    - `maintenance_compaction_partitions_per_job: int = Field(default=10, ge=1, le=1000)`;
    - `maintenance_compaction_quiet_seconds: int = Field(default=120, ge=0)`;
    - `maintenance_compaction_max_quiet_wait_seconds: int = Field(default=3600, ge=0)`.

    These are flat `maintenance_*` fields, so `test_settings_hold_no_round_scheduling_or_candidate_selection_group` (no `compaction` field) still holds.
  - `build_partition_selection_settings(settings: AppSettings) -> PartitionSelectionSettings`.
  - `build_use_cases(..., partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS)` passes it to `PlanTableMaintenanceService` beside `metrics_store` and `cooldowns`. `build_connected_use_cases` passes `build_partition_selection_settings(settings)`.
  - `PlatformSettings` gains three ints: `compaction_partitions_per_job`, `compaction_quiet_seconds` and `compaction_max_quiet_wait_seconds`. `build_platform_settings` fills them.
  - `GetPlatformSettingsService` returns five groups, with `partition_selection` as in Global Constraints. The OpenAPI document does not change: the response is generic.
  - Chart:
    - `values.yaml` gains `worker.compactionPartitionsPerJob: 10`, `worker.compactionQuietSeconds: 120` and `worker.compactionMaxQuietWaitSeconds: 3600`, after `failureBackoffCapSeconds`.
    - `configmap.yaml` renders them into the three `GLAC_MAINTENANCE_COMPACTION_*` vars, after `GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS`.

- [ ] **Step 1: Write the failing tests**

```python
def test_app_settings_read_the_partition_selection_env(monkeypatch):
    monkeypatch.setenv("GLAC_MAINTENANCE_COMPACTION_PARTITIONS_PER_JOB", "4")
    monkeypatch.setenv("GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS", "0")
    monkeypatch.setenv("GLAC_MAINTENANCE_COMPACTION_MAX_QUIET_WAIT_SECONDS", "600")
    s = AppSettings()
    assert (s.maintenance_compaction_partitions_per_job, s.maintenance_compaction_quiet_seconds,
            s.maintenance_compaction_max_quiet_wait_seconds) == (4, 0, 600)

@pytest.mark.parametrize("value", ["0", "1001"])
def test_partitions_per_job_out_of_range_is_refused(monkeypatch, value):
    monkeypatch.setenv("GLAC_MAINTENANCE_COMPACTION_PARTITIONS_PER_JOB", value)
    with pytest.raises(ValueError, match="maintenance_compaction_partitions_per_job"):
        AppSettings()

@pytest.mark.parametrize("name", ["QUIET_SECONDS", "MAX_QUIET_WAIT_SECONDS"])
def test_negative_quiet_is_refused(monkeypatch, name):
    monkeypatch.setenv(f"GLAC_MAINTENANCE_COMPACTION_{name}", "-1")
    with pytest.raises(ValueError, match=f"maintenance_compaction_{name.lower()}"):
        AppSettings()

def test_partition_selection_defaults_match_the_domain_defaults():
    s, d = AppSettings(), PartitionSelectionSettings.platform_default()
    assert (s.maintenance_compaction_partitions_per_job, s.maintenance_compaction_quiet_seconds,
            s.maintenance_compaction_max_quiet_wait_seconds) == (
        d.partitions_per_job, d.quiet_period.total_seconds(), d.max_quiet_wait.total_seconds())

def test_build_partition_selection_settings():
    s = AppSettings(maintenance_compaction_partitions_per_job=4, maintenance_compaction_quiet_seconds=0,
                    maintenance_compaction_max_quiet_wait_seconds=600)
    assert build_partition_selection_settings(s) == PartitionSelectionSettings(
        partitions_per_job=4, quiet_period=timedelta(0), max_quiet_wait=timedelta(seconds=600))

def test_platform_settings_list_partition_selection():
    groups = GetPlatformSettingsService(settings).execute(GetPlatformSettingsUseCaseInput()).groups
    assert [g.key for g in groups] == ["execution_capacity", "compute_sizes", "cooldown_and_backoff",
                                       "partition_selection", "discovery"]
    assert groups[3].title == "Compaction partition selection"
    assert [(i.key, i.label, i.value, i.unit) for i in groups[3].items] == [
        ("maintenance_compaction_partitions_per_job", "Partitions per job", 10, "partitions"),
        ("maintenance_compaction_quiet_seconds", "Quiet period", 120, "seconds"),
        ("maintenance_compaction_max_quiet_wait_seconds", "Longest wait for quiet", 3600, "seconds"),
    ]

def test_build_platform_settings_copies_the_partition_selection(): ...   # AppSettings(…=4, 0, 600) → PlatformSettings
                                                                         #   compaction_* fields 4, 0, 600

def test_the_planner_is_given_the_partition_selection():
    # test_build_use_cases.py, beside test_the_planner_is_given_the_cooldowns and built the same way
    ...  # built with partition_selection=X → planner._partition_selection == X; built without → DEFAULT_PARTITION_SELECTION_SETTINGS

def test_the_planner_reads_the_partition_selection_the_settings_say(tmp_path):
    # test_build_connected_use_cases.py, built like test_the_planner_reads_the_cooldowns_the_settings_say
    ...  # sqlite_settings(maintenance_compaction_quiet_seconds=0) → planner._partition_selection == build_partition_selection_settings(settings)

def test_platform_settings_route_lists_partition_selection(client): ...   # GET /v1/platform-settings → group keys as above
```

The `...` bodies copy the arrange part of the test named in their comment; the assertion is the one after the arrow.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/bootstrap tests/context/table_maintenance/application/service/table_maintenance_run/test_get_platform_settings.py tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run/test_platform_settings_route.py -k "partition_selection or platform_settings" -v`
- [ ] **Step 3: Implement**, then update `storyData.ts` to the five groups, with the copy from Global Constraints.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`; `<vitest> PlatformSettingsPage`. Then `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c "GLAC_MAINTENANCE_COMPACTION_"` prints `3`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): make compaction partition selection platform settings (KCL-94)`.

### Task 7: A run records the `where` clauses it compacts with (backend)

**Files:**
- Modify:
  - `TM/application/domain/model/table_maintenance_run/operation_run.py` and `table_maintenance_run.py`;
  - `TM/application/port/inbound/table_maintenance_run/create_table_maintenance_run/input.py`;
  - `TM/application/service/table_maintenance_run/create_table_maintenance_run.py` and `table_maintenance_run_output_fields.py`;
  - `TM/application/port/outbound/table_maintenance_run/__init__.py`: re-export `SpecFilter`;
  - `TM/adapter/outbound/table_maintenance_run/sql/table_maintenance_run_row_mapper.py` (`_encode_operation` / `_decode_operation`);
  - `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`;
  - `TM/adapter/inbound/web/table_maintenance_run/dto.py`;
  - `openapi.json` and the generated client (`task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`).
- Test (all under `tests/context/table_maintenance/`):
  - `application/domain/model/table_maintenance_run/test_table_maintenance_run.py` and `test_operation_run.py`;
  - `application/service/table_maintenance_run/test_table_maintenance_run_services.py`;
  - `adapter/outbound/table_maintenance_run/test_table_maintenance_runs_sql_repo.py`;
  - `adapter/hybrid/temporal/inbound/test_table_maintenance_workflow.py` (the fakes record `created` requests) and `test_run_activity_payloads.py`;
  - `adapter/inbound/web/table_maintenance_run/test_table_maintenance_run_routes.py`.

**Interfaces:**
- Consumes: the plan output `filters` (Task 4). At HEAD the workflow already submits `operation["filters"]` with every attempt.
- Produces:
  - `OperationRun.filters: tuple[SpecFilter, ...] = ()`.
  - `TableMaintenanceRun.create(..., execution_ref, priority=TablePriority.P3, filters: Mapping[MaintenanceOperation, Sequence[SpecFilter]] | None = None)`. It refuses filters with `InvalidRunTransition` for an operation other than `REWRITE_DATA_FILES`, or for one not in the run.
  - `CreateTableMaintenanceRunUseCaseInput.Filter(spec_id: int, where: str)` and `filters: dict[str, tuple[Filter, ...]] = Field(default_factory=dict)`, keyed by operation name. The service parses each key with `MaintenanceOperation(key)` inside `translate_domain_errors()`, so an unknown name is a `ValidationError`.
  - The workflow adds `"filters": {op["operation"]: op["filters"] for op in operations if op["filters"]}` to the `CREATE_MAINTENANCE_RUN` payload. The submit payload is unchanged.
  - The run's `operations_json` entry gains `"filters": [{"spec_id", "where"}]`; a missing key reads as `()`. `table_maintenance_run_output_fields` adds `"filters"` with the same shape.
  - `TableMaintenanceRunFilterApiResponse(spec_id: int, where: str)`. `TableMaintenanceRunOperationApiResponse.filters: list[TableMaintenanceRunFilterApiResponse] = Field(description="The where clauses each job of this operation passes to rewrite_data_files, one per partition spec; empty: the whole table.")`.

- [ ] **Step 1: Write the failing tests**

```python
EU = SpecFilter(spec_id=0, where="(`region` = 'eu')")

def test_a_run_keeps_the_compaction_filters():
    run = TableMaintenanceRun.create(RUN_ID, TABLE_ID, TriggerType.SCHEDULED, [REWRITE, EXPIRE], NOW,
                                     execution_ref="wf", filters={REWRITE: [EU]})
    assert run.operations[0].filters == (EU,)
    assert run.operations[1].filters == ()

def test_filters_on_another_operation_are_refused():
    with pytest.raises(InvalidRunTransition):
        TableMaintenanceRun.create(RUN_ID, TABLE_ID, TriggerType.SCHEDULED, [REWRITE, EXPIRE], NOW,
                                   execution_ref="wf", filters={EXPIRE: [EU]})

def test_filters_for_an_operation_not_in_the_run_are_refused():
    with pytest.raises(InvalidRunTransition):
        TableMaintenanceRun.create(RUN_ID, TABLE_ID, TriggerType.SCHEDULED, [EXPIRE], NOW,
                                   execution_ref="wf", filters={REWRITE: [EU]})

def test_an_operation_run_without_filters_is_the_whole_table():
    assert OperationRun(operation=REWRITE).filters == ()

def test_create_run_service_saves_the_filters(): ...      # input filters {"rewrite_data_files": ({"spec_id": 0, "where": "x"},)}
                                                          # → runs_repo.get(id).operations[0].filters == (SpecFilter(spec_id=0, where="x"),)
def test_create_run_service_refuses_an_unknown_operation_key(): ...  # filters {"compact": (...)} → raises ValidationError, no run stored
def test_sql_round_trip_keeps_the_filters(): ...          # a run created with {REWRITE: [EU]} → get(...).operations[0].filters == (EU,)
def test_a_stored_operation_without_filters_reads_none(): ...  # raw UPDATE removing "filters" from operations_json → filters == ()
def test_the_workflow_creates_the_run_with_the_plans_filters(): ...
    # a plan of rewrite_data_files only, filters [{"spec_id": 0, "where": "rewrite_data_files = 1"}]
    # → h.fakes.created[0]["filters"] == {"rewrite_data_files": [{"spec_id": 0, "where": "rewrite_data_files = 1"}]}
def test_the_workflow_sends_no_filters_for_a_whole_table_plan(): ...  # plan filters [] → h.fakes.created[0]["filters"] == {}
def test_get_run_shows_the_filters(client): ...           # run stored with {REWRITE: [EU]}
                                                          # → body["operations"][0]["filters"] == [{"spec_id": 0, "where": "(`region` = 'eu')"}]
def test_get_run_shows_empty_filters_for_the_whole_table(client): ...  # run stored without filters → every operation's "filters" == []
def test_list_runs_of_a_table_shows_the_filters(client): ...  # GET /v1/tables/{uuid}/table-maintenance-runs → same filters as above
```

The `...` bodies copy the arrange part of the neighbouring tests in the same file, and assert what follows the arrow.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "filters" -v`
- [ ] **Step 3: Implement**, then run `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`, including `tests/architecture/test_temporal_workflow_determinism.py`, `test_inbound_port_field_types.py` and `test_dto_naming.py`. Do not commit yet: the console must compile against the new client (Task 8).

### Task 8: The console shows what a compaction compacted

**Files:**
- Create: `lib/compactionScopeText.ts`, `lib/compactionScopeText.test.ts`
- Modify:
  - `components/tabs/MaintenanceTab.tsx` and `components/tabs/MaintenanceTab.test.tsx`;
  - every maintenance-run operation fixture gets `filters`: `stories/storyData.ts`, `lib/anyRunInFlight.test.ts` and the fixtures inside `MaintenanceTab.test.tsx`. These are the files at HEAD that build `attempt_history`; `test/fixtures.ts` holds none.
  - `pages/TablePage.stories.tsx`: add `MaintenancePartitionScope` (one run whose compaction has two filters, one long `where` of 10 partitions, and one whole-table manual run) and `MaintenancePartitionScopePhone` (the same at `PHONE`).
- Test: `compactionScopeText.test.ts`, `MaintenanceTab.test.tsx`, the two new stories.

**Interfaces:**
- Consumes: the generated `TableMaintenanceRunOperationApiResponse.filters` (Task 7).
- Produces:
  - `compactionScopeText(op: TableMaintenanceRunOperationApiResponse): {summary: string; wheres: {specId: number; where: string}[]} | null`.
    - It returns `null` for every operation other than `rewrite_data_files`.
    - Empty `filters` gives `{summary: "Whole table", wheres: []}`.
    - Otherwise it gives `{summary: "Partitions over the target", wheres: [...]}` in the API's order.
  - `OperationDetail` adds a `<p className="type-body-small">Scope: {summary}</p>` under its header row.
    - For each where it adds an item in a `<ul className="type-code text-on-surface-variant">`, rendered `spec {specId}: {where}`.
    - Each item has `break-all`, so a long clause wraps with no horizontal page scroll at phone width.

- [ ] **Step 1: Write the failing tests and stories:**
  - `compactionScopeText`:
    - `expire_snapshots` gives `null`;
    - `rewrite_data_files` with `filters: []` gives `{summary: "Whole table", wheres: []}`;
    - two filters (spec 0 and spec 1) give `summary` "Partitions over the target" and `wheres` `[{specId: 0, …}, {specId: 1, …}]`.
  - `MaintenanceTab`:
    - an expanded run shows "Scope: Partitions over the target" and `` spec 0: (`region` = 'eu') ``;
    - a manual run shows "Scope: Whole table";
    - an `expire_snapshots` operation shows no "Scope:" line.
  - Stories: `MaintenancePartitionScopePhone` passes `expectNoHorizontalPageScroll`, as the other phone stories in `TablePage.stories.tsx` do.
- [ ] **Step 2: Run and watch them fail:** `<vitest> compactionScopeText MaintenanceTab`
- [ ] **Step 3: Implement** with design-system parts only (`src/data-platform/frontend/CLAUDE.md`).
- [ ] **Step 4: Run and watch them pass:** `<vitest>`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit Tasks 7 and 8 together.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): record and show the where clauses a compaction run passes (KCL-94)` with the backend, `openapi.json`, the generated client and the console.

### Task 9: e2e script and documentation

**Files:**
- Modify:
  - `platform/25-lakehouse-control-plane/e2e.sh` and `platform/25-lakehouse-control-plane/README.md`;
  - `src/data-platform/backend/CLAUDE.md`;
  - `src/data-platform/frontend/CLAUDE.md`, only if it describes the Maintenance tab (at HEAD it does not name it; then leave it);
  - `docs/agents/known-follow-ups.md` and `docs/agents/project-history.md`.

**Interfaces:**
- Consumes: the run API `filters` (Task 7) and the settings (Task 6).

- [ ] **Step 1: e2e.** Read `e2e.sh` at HEAD first. At HEAD, `assert_whole_table_compaction` reads the plan from `maintenance_workflow_input`, and the regions table holds `'north'` and `'o''neil'`.
  - Add `assert_partition_compaction run_id…`.
    - For each run, `GET /v1/table-maintenance-runs/{id}` must have exactly one `rewrite_data_files` operation, with non-empty `filters` and no empty `where`.
    - It prints each `where` with `progress`.
    - Across the runs, at least one `where` must hold the escaped quote `'o\'neil'`: the check of the pre-KCL-93 `assert_partition_filter`.
  - Use it for `${REGIONS_RUNS}` in place of `assert_whole_table_compaction`.
  - `assert_whole_table_compaction` now reads the run API (`filters == []` for `rewrite_data_files`) in place of the workflow input. It keeps being used for `${ORDERS_MANUAL_RUN_ID}`.
  - The `tm-e2e-regions` description becomes "e2e: scheduled per-partition compaction".
  - After the regions run, print the results of `rewrite_data_files` in the regions reconciliations, with no assertion since timing decides them, so a `waiting_for_writes` shows in the log.
  - Run `uv run --directory /Users/kcl/Projects/retail-lakehouse pre-commit run shellcheck --all-files`.
- [ ] **Step 2: Docs.**
  - README:
    - Replace "`per: partition` decides only whether compaction is due; a run compacts the whole table either way" with one paragraph. It covers the scheduled selection, the cap, the quiet period, the maximum wait, `waiting_for_writes`, the manual whole-table run and the run's `filters`.
    - The platform settings paragraph: "four groups (execution capacity, Spark sizes, cooldown and backoff, discovery)" becomes five groups, with compaction partition selection before discovery. Add the three chart keys with their defaults and env names.
    - e2e step 6: the regions table is compacted per partition, with the escaped quote checked.
  - Backend `CLAUDE.md`:
    - In the policy paragraph, replace "`per` decides only whether compaction is due (a run compacts the whole table)" with "`per: partition` compacts only the partitions over the target on a scheduled plan (see below)".
    - Add a short paragraph after it. It covers the over-target record on `Table` with its narrow write, the two pure functions, the new verdict and result, `OperationRun.filters`, and the rule that the selection reuses `compute_reducible_files` while `TableMetrics` stays table-level.
  - `known-follow-ups.md`:
    - Remove the two entries "`assess_maintenance` still selects the qualifying partitions … until KCL-94" and "`per: partition` decides only whether compaction is due … until KCL-94".
    - Add four entries, each tagged with the date it lands and KCL-94:
      - Left-over and waiting partitions wait for the next check that `on:` and the rewrite cooldown allow. A table with 100 partitions over the target and the default cap takes ten cooldowns. There is no recheck timer.
      - The over-target record grows with the number of partitions over the target. It is one JSON column on the table row.
      - `per: table` ignores the quiet period, so it can compact a partition still being written.
      - A manual compaction always rewrites the whole table.
  - `project-history.md`: one KCL-94 line, dated the day it lands. It names:
    - the three env vars and chart keys with their defaults;
    - the verdict and result `waiting_for_writes`;
    - the measurements `selected_partitions` and `waiting_partitions`;
    - `Table.over_target_partitions`;
    - `filters` on each run operation in the API.

    It ends with "No migration: rebuild the cluster."
- [ ] **Step 3: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `docs(table-maintenance): describe partition-selected compaction and check it in the e2e (KCL-94)`.

### Task 10: Verify on a rebuilt cluster (controller, batched with KCL-95)

The controller runs this in the rebuild batched with KCL-95; it does not run per issue. The rebuild that verifies KCL-91, KCL-96 and KCL-97 comes before this plan and does not cover it. The temporary values below are never committed.

- [ ] **Step 1: Rebuild.** Run `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse onboard KUBE_CONTEXT=retail-lakehouse`. Then `task -d /Users/kcl/Projects/retail-lakehouse apps:validate KUBE_CONTEXT=retail-lakehouse` must exit 0.
- [ ] **Step 2: Settings.**
  - `GET /v1/platform-settings` has the group `partition_selection` with 10, 120 and 3600, between `cooldown_and_backoff` and `discovery`.
  - The console's Platform settings page shows "Compaction partition selection" with "10 partitions", "2 min" and "1 h".
- [ ] **Step 3: Lower two values for the test.**
  - Set them in `values.yaml`: `worker.rewriteDataFilesCooldownSeconds: 60` and `worker.compactionMaxQuietWaitSeconds: 600`.
  - Rerun `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/bootstrap.sh`, never `kubectl patch configmap`.
  - Create the namespace `iceberg.kcl94` and a rule that manages `iceberg / kcl94 / *`: a discovery rule, or a discovery policy once KCL-71 has landed.
  - Attach a policy `kcl94` to the namespace:
    - `on: {schedule: {every_seconds: 300}, catalog_commit: {debounce_seconds: 60}}`;
    - `rewrite_data_files: {target: {reducible_files: {at_most: 1}, per: partition}, options: {min_input_files: 2}}`;
    - no other block.

    The option is needed because Iceberg's default `min-input-files` is 5, and a 3-file partition would stay over the target forever.
- [ ] **Step 4: Cap and order.**
  - Create `iceberg.kcl94.capped` (`region VARCHAR, id BIGINT`, partitioned by `region`).
  - In one `trino_sql` call, insert `n + 1` single-row commits into `r01` … `r12` (region `rNN` gets `NN + 1` rows). So `rNN` has `NN` reducible files, and `r01` is not over the target.
  - After the quiet period, check the first compaction run:
    - its `filters` holds one `where` naming `r03` … `r12` and neither `r01` nor `r02`;
    - its reconciliation shows `qualifying_partitions` 11 and `selected_partitions` 10.
  - The run succeeds, and `capped$files` drops for those ten partitions. The Overview's reducible files card (KCL-96) drops by the same amount after the next check.
  - The next check after the 60 s cooldown compacts `r02` alone.
- [ ] **Step 5: Quiet period and maximum wait.**
  - Create `iceberg.kcl94.hot` (partitioned by `region`) and insert 4 single-row commits into `cold`.
  - The commit-window check about 60 s later records `rewrite_data_files` `waiting_for_writes`, with `next_eligible_at` about 120 s after the last write. It starts no run.
  - Right after that record, insert 3 rows into `hot`, so it is over the target. Then keep inserting one row into `hot` every 30 s for 15 minutes.
  - The next check, more than 120 s after the last `cold` write, starts a run that compacts `cold` only. Its `where` names `cold` and not `hot`, and its reconciliation shows `selected_partitions` 1 and `waiting_partitions` 1.
  - About 600 s after `hot` first went over the target, a run compacts `hot` while the writes go on: its `where` names `hot`.
  - Every run succeeds, with no commit conflict failure.
- [ ] **Step 6: Transforms and spec evolution.**
  - Create `iceberg.kcl94.events` (`id BIGINT, ts TIMESTAMP(6) WITH TIME ZONE`, partitioned by `ARRAY['day(ts)', 'bucket(id, 4)']`). Insert 3 single-row commits for each of two days and two buckets.
  - Then run `ALTER TABLE iceberg.kcl94.events SET PROPERTIES partitioning = ARRAY['day(ts)']` and insert 3 more rows for one day.
  - Check the next compaction run:
    - it has two `filters`: spec 0 with `system.days` and `system.bucket` terms, and spec 1 with `system.days`;
    - its driver log shows two `CALL`s;
    - it succeeds.
- [ ] **Step 7: Manual run and console.**
  - A manual `rewrite_data_files` on `kcl94.capped` records `filters: []`.
  - The console's Maintenance tab:
    - the runs above read "Scope: Partitions over the target", with their `spec N: …` lines;
    - the manual run reads "Scope: Whole table";
    - at phone width the long `where` wraps, with no horizontal page scroll.
  - The Reconciliations tab reads "Waiting for writes" with its sentence for the Step 5 check, and "This run compacts 10 of them." for the Step 4 run.
- [ ] **Step 8: Restore and finish.**
  - Restore `values.yaml` with `git -C /Users/kcl/Projects/retail-lakehouse checkout -- platform/25-lakehouse-control-plane/chart/values.yaml`, then rerun `bootstrap.sh`.
  - `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` must pass, with the regions run's `where` holding `'o\'neil'`.
  - Then run `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`. Record the results on KCL-94 in a dated comment, and push only when the user asks.
