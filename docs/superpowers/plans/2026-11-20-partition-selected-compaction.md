# Partition-Selected Compaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With `per: partition`, a scheduled `rewrite_data_files` compacts only the partitions over `reducible_files.at_most`. A job takes at most N of them, those with the most reducible files first. A partition written within the quiet period waits, unless it has been over the target for longer than the maximum wait. Each run records the `where` clauses it passed, and the API and the console show them.

**Architecture:** Two pure domain functions do the selection. `track_over_target_partitions` keeps, per partition over the target, the time it was first seen over it. `select_compaction_partitions` applies the quiet period, the maximum wait and the per-job cap. `assess_maintenance` calls both. It plans the selected partitions, or reports the new verdict `waiting_for_writes` when every partition over the target is still being written, and it returns the updated over-target record. The plan service saves that record on the `Table` through a narrow repository write and renders the `where` clauses with the existing `build_partition_filters`. The maintenance workflow passes those clauses to run creation, so every `OperationRun` keeps the `filters` its jobs were submitted with. Three platform settings (`GLAC_MAINTENANCE_COMPACTION_*`) shape the selection and appear on the Platform settings page.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK, Helm, React + TanStack Query + orval + MSW, Storybook/vitest.

**Spec:** Linear KCL-94 (https://linear.app/kcl10/issue/KCL-94) and its 2026-11-19 comment (the selection steps; "since when" lives on the table; a pure function, test-first; no halving after OOM). Also `docs/adr/0012-policies-on-the-catalog-hierarchy.md`, section "Compacting only the partitions that need it". This plan builds on KCL-93 (plan `docs/superpowers/plans/2026-11-20-per-table-maintenance-workflow.md`: one workflow per table, whole-table compaction, no rounds, candidates or admission) and KCL-91 (plan `docs/superpowers/plans/2026-11-20-maintenance-policy-target-state.md`: `rewrite_data_files.target = {reducible_files: {at_most}, per}`, cooldowns as platform settings; its "Boundaries" section hands this plan partition selection, the three settings and the run's `where`). KCL-91's final fix wave is editing files on main, mostly `table_maintenance_policy`, `resolve_snapshot_retention`, the reconciliation workflow, the Spark `sql_builder`, the console policy pages, `e2e.sh` and the wave-25 README. **Read each file at HEAD before changing it; never apply a step against a remembered version.**

## Global Constraints

Decisions this plan makes are marked **(decided)** with the reason. The rest is copied from the issue, its comment and ADR 0012.

- **Over the target (KCL-91, unchanged):** a partition is over the target when its `compute_reducible_files(p, target_file_size)` is `> at_most`. The target file size is the table's `write.target-file-size-bytes`, else 512 MiB. Every partition of every spec in the observation is compared, including the partitions of an older spec (the observation already lists them by `(spec_id, values)`).
- **Selection applies only to a scheduled plan with `per: partition` (decided).**
  - `per: table` compares the table's total and rewrites the whole table, with no `where`, no cap and no quiet period. The issue's comment says `per: table` "只比整張表，不帶 where", and the three settings are about choosing partitions.
  - A manual run of `rewrite_data_files` still compacts the whole table. A manual run assesses nothing, and it is the escape hatch a person uses.
- **Order and cap (issue, ADR):** the partitions allowed to run are sorted by reducible files, most first. Ties go by `spec_id` ascending, then by `repr(values)` ascending **(decided: deterministic, so a retried plan picks the same set)**. The job takes the first `partitions_per_job`. The rest stay over the target and are taken by a later check.
- **Quiet period and maximum wait (issue, decided in detail):** a partition over the target **waits** when all three of these hold:
  - its `last_written_at` is known;
  - `now - last_written_at < quiet_period`;
  - `now - over_target_since < max_quiet_wait`.

  Otherwise it is allowed to run. When `last_written_at` is unknown (its snapshot has expired), the partition counts as quiet. A `last_written_at` in the future (clock skew) makes the partition wait, bounded by the maximum wait. A `quiet_period` or `max_quiet_wait` of `0` means nothing ever waits.
- **"Over the target since" lives on the table (comment):** `Table.over_target_partitions: tuple[OverTargetPartition, ...]` records each partition currently over the target with `since`, the time the first plan saw it over. A partition no longer over the target is dropped from it, and there is no separate SQL table.
  - **When the record is replaced (decided).** Every scheduled plan of a managed, observed table replaces the record with the assessment's, including a dry run, a compaction in cooldown and one needing attention, since being over the target does not depend on them. A policy with no `rewrite_data_files` block, or one with `per: table`, empties the record.
  - **When it is left alone.** A manual plan, a skip and the health read do not touch it.
- **The record has its own write (decided: mirrors `record_last_commit`, so a plan holding an old copy of the table never puts back state another writer stored since, and a lost race costs only a later `since`).** `TablesRepo.record_over_target_partitions(table_id, partitions) -> bool` writes only the column `over_target_partitions_json`, and never once the table is dropped. `TablesRepo.update` never writes that column. Recording it does not move `updated_at`.
- **New verdict `waiting_for_writes` (decided: a due verdict without a run is refused by `RecordTableReconciliationService`, and "not needed" would contradict the met measurement).** When at least one partition is over the target and every one of them waits:
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

  The ceiling of 1000 is decided: it bounds the size of one `where`. The quiet period of 120 s is the old candidate default, "a few minutes" in the ADR. The ConfigMap gives these settings to the api and the worker alike.
- **Platform settings page (decided):** a fifth group, key `partition_selection`, title "Compaction partition selection", placed between `cooldown_and_backoff` and `discovery`. Its items, in this order:

  | Key | Label | Unit | Description |
  |---|---|---|---|
  | `maintenance_compaction_partitions_per_job` | "Partitions per job" | `partitions` | "The most partitions one rewrite data files job compacts; those with the most reducible files go first, the rest wait for a later check." |
  | `maintenance_compaction_quiet_seconds` | "Quiet period" | `seconds` | "A partition written more recently than this waits for a later check, so compaction does not race its writers." |
  | `maintenance_compaction_max_quiet_wait_seconds` | "Longest wait for quiet" | `seconds` | "A partition over its target for this long is compacted even while it is still being written." |
- **The run records its `where` (issue: until KCL-95 changes the run model, it is kept on today's operation record).**
  - **Model.** `OperationRun.filters: tuple[SpecFilter, ...] = ()` holds the clauses every attempt of the operation is submitted with; `()` means the whole table. It is set when the run is created, from the plan. Only `rewrite_data_files` may hold filters: any other operation is refused with `InvalidRunTransition`.
  - **API.** Each operation of `GET /v1/table-maintenance-runs/{run_id}` and `GET /v1/tables/{table_uuid}/table-maintenance-runs` carries `filters: [{"spec_id": int, "where": str}]`.
- **No other change to execution (KCL-93 comment):** no halving of the partitions after an out-of-memory failure, since the size escalation S/M/L handles it; size escalation, the result callback and `procedure_args` are unchanged.
- **No extra wake (decided: the issue says waiting partitions are "這次先跳過", skipped this time).** A waiting or left-over partition is taken by the next check that `on:` and the cooldown allow. The reconciliation gets no recheck timer. This is listed in known-follow-ups.
- **No data migration and no new `workflow.patched` markers.** A missing `over_target_partitions_json`, or a stored operation without `filters`, reads as `()`. The cluster is rebuilt before deploy (`task offboard`, `task onboard KUBE_CONTEXT=retail-lakehouse`), batched with KCL-91 and KCL-95.
- **Boundary with KCL-95 (state it, do not build it):** KCL-95 makes a run one operation and moves the Maintenance, Reconciliations and Commits tabs to side panels. Here the run model, its status rules, the callback route and the tab layouts stay as they are. `filters` is one more field on today's `OperationRun`, which KCL-95 moves onto the single-operation run with the other procedure arguments, and the Maintenance tab gets one "Scope" line per compaction, which KCL-95 moves into its panel.
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

- A tracked partition whose values survive a JSON round trip (an int, a float `1.5`, a bool, a `None` value, a string with a quote) still matches the observed partition after store and load, so its `since` is kept and not restarted on every plan (Tasks 1 and 2).
- A table whose spec evolved keeps spec 0 and spec 1 partitions with equal values as two entries. A selection across both specs gives two filters, so two `CALL`s in one job (Tasks 1 and 4).
- A `last_written_at` later than `now` (writer clock skew) makes the partition wait, and it is compacted once it has been over the target for `max_quiet_wait`, never held forever (Task 1).
- A selected partition the builder cannot render (a `timestamp_ns` day partition) compacts the whole table. The run's `filters` is then `[]`, matching what Spark ran, not the unrendered selection (Task 4).
- A plan that races a result record or a rename loses neither. The over-target record is written only by its narrow write, and `update` of an older copy keeps the stored record (Task 2).

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `TM` = `context/table_maintenance`; `TEMPORAL` = `TM/adapter/hybrid/temporal`; tests mirror under `tests/`. Frontend paths are relative to `src/data-platform/frontend/src/`.

| File | Responsibility |
|---|---|
| `TM/application/domain/model/shared/{over_target_partition,partition_selection}.py` (new) | a tracked partition; the result of a selection |
| `TM/application/domain/model/table/{partition_selection_settings,default_partition_selection_settings}.py` (new) | cap, quiet period, maximum wait |
| `TM/application/domain/service/table/{track_over_target_partitions,select_compaction_partitions}.py` (new) | the two pure functions |
| `TM/application/domain/model/table/table.py`, `TM/application/port/outbound/table/tables_repo.py`, `TM/adapter/outbound/table/sql/{tables_table,table_row_mapper,tables_sql_repo}.py` | the table keeps its over-target partitions |
| `TM/application/domain/model/shared/{operation_verdict,maintenance_assessment}.py`, `TM/application/domain/service/table/assess_maintenance.py` | selection in the assessment |
| `TM/application/service/table/{plan_table_maintenance,get_table_health}.py` | `where` clauses, record written, settings in |
| `TM/application/domain/model/table_reconciliation/operation_result.py`, `TM/application/service/table_reconciliation/record_table_reconciliation.py` | `waiting_for_writes` recorded |
| `bootstrap/configs/app_settings.py`, `bootstrap/container/{build_partition_selection_settings (new),build_platform_settings,build_use_cases,build_connected_use_cases}.py`, `TM/application/domain/model/shared/platform_settings.py`, `TM/application/service/table_maintenance_run/get_platform_settings.py` | settings and the page group |
| `TM/application/domain/model/table_maintenance_run/{operation_run,table_maintenance_run}.py`, `create_table_maintenance_run` port and service, `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`, runs row mapper, `table_maintenance_run_output_fields.py`, `TM/adapter/inbound/web/table_maintenance_run/dto.py` | the run records its `where` |
| `components/tabs/reconciliationText.ts`, `lib/compactionScopeText.ts` (new), `components/tabs/MaintenanceTab.tsx`, `stories/storyData.ts`, `test/fixtures.ts` | console |
| `platform/25-lakehouse-control-plane/chart/{values.yaml,templates/configmap.yaml}`, `e2e.sh`, `README.md` | chart, e2e, docs |

---

### Task 1: The two selection functions

New files only.

**Files:**
- Create: `TM/application/domain/model/shared/over_target_partition.py`, `TM/application/domain/model/shared/partition_selection.py` (export both from `TM/application/domain/model/shared/__init__.py`); `TM/application/domain/model/table/partition_selection_settings.py`, `TM/application/domain/model/table/default_partition_selection_settings.py` (export from `TM/application/domain/model/table/__init__.py`); `TM/application/domain/service/table/track_over_target_partitions.py`, `TM/application/domain/service/table/select_compaction_partitions.py` (export from `TM/application/domain/service/table/__init__.py`)
- Test: new `tests/context/table_maintenance/application/domain/model/table/test_partition_selection_settings.py`, `tests/context/table_maintenance/application/domain/service/table/test_track_over_target_partitions.py`, `tests/context/table_maintenance/application/domain/service/table/test_select_compaction_partitions.py`

**Interfaces:**
- Produces (all `ValueObject`):
  - `OverTargetPartition(spec_id: int, values: tuple[str | int | float | bool | None, ...], since: datetime)` with `is_of(partition: PartitionStats) -> bool` (equal `spec_id` and `values`).
  - `PartitionSelectionSettings(partitions_per_job: int, quiet_period: NonNegativeDuration, max_quiet_wait: NonNegativeDuration)`. `partitions_per_job` is from 1 to 1000, else `InvariantViolation` "must be between 1 and 1000". `platform_default()` returns `10`, `timedelta(seconds=120)`, `timedelta(hours=1)`. `DEFAULT_PARTITION_SELECTION_SETTINGS = PartitionSelectionSettings.platform_default()`.
  - `PartitionSelection(selected: tuple[PartitionStats, ...] = (), waiting: tuple[PartitionStats, ...] = (), waiting_until: datetime | None = None)` with `@property all_waiting -> bool` (`waiting` non-empty and `selected` empty).
  - `track_over_target_partitions(previous: Sequence[OverTargetPartition], over_target: Sequence[PartitionStats], now: datetime) -> tuple[OverTargetPartition, ...]`. It returns one entry per partition of `over_target`, in that order. The entry keeps the previous `since` when it was tracked, else its `since` is `now`. A previous entry not in `over_target` is dropped.
  - `select_compaction_partitions(over_target: Sequence[tuple[PartitionStats, int]], tracked: Sequence[OverTargetPartition], now: datetime, settings: PartitionSelectionSettings) -> PartitionSelection`. Each pair is a partition over the target and its reducible files. The waiting rule, the order and the cap are those of Global Constraints. `waiting_until` is the minimum of `min(last_written_at + quiet_period, since + max_quiet_wait)` over the waiting partitions, and `None` when none waits. A partition missing from `tracked` counts as `since = now`.

- [ ] **Step 1: Write the failing tests**

```python
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)
SETTINGS = PartitionSelectionSettings.platform_default()

def p(spec_id, *values, written=None, files=10): ...   # PartitionStats with last_written_at=written

def test_platform_default_selection_settings():
    s = PartitionSelectionSettings.platform_default()
    assert (s.partitions_per_job, s.quiet_period, s.max_quiet_wait) == (10, timedelta(minutes=2), timedelta(hours=1))

@pytest.mark.parametrize("n", [0, 1001])
def test_partitions_per_job_out_of_range_is_refused(n): ...          # InvariantViolation

def test_a_new_partition_over_target_is_tracked_since_now():
    assert track_over_target_partitions((), [p(0, "eu")], NOW) == (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)

def test_a_tracked_partition_keeps_its_since(): ...                  # previous since NOW-2h kept
def test_a_partition_back_under_target_is_dropped(): ...              # previous eu, over_target [] → ()
def test_the_same_values_in_two_specs_are_two_entries(): ...          # p(0,"eu"), p(1,"eu") → 2 entries, since per spec
def test_a_round_tripped_entry_still_matches(): ...                   # OverTargetPartition.from_primitives(entry.to_primitives()).is_of(p(0, 1, 1.5, True, None, "o'neil"))

def test_nothing_over_target_selects_nothing():
    assert select_compaction_partitions([], [], NOW, SETTINGS) == PartitionSelection()

def test_quiet_partitions_are_all_selected_under_the_cap(): ...       # 3 quiet → selected all 3, waiting ()
def test_the_cap_takes_the_most_reducible_first():
    over = [(p(0, f"r{i:02}"), i) for i in range(1, 13)]             # 12 partitions, reducible 1..12
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [s.values[0] for s in got.selected] == [f"r{i:02}" for i in range(12, 2, -1)]

def test_ties_break_by_spec_then_values(): ...                        # equal reducible: (0,"b"), (0,"a"), (1,"a") → (0,"a"), (0,"b"), (1,"a")
def test_a_recently_written_partition_waits():
    hot = p(0, "hot", written=NOW - timedelta(seconds=30))
    got = select_compaction_partitions([(hot, 5), (p(0, "cold"), 5)], [], NOW, SETTINGS)
    assert ([s.values for s in got.selected], [w.values for w in got.waiting]) == ([("cold",)], [("hot",)])
    assert got.waiting_until == NOW + timedelta(seconds=90)

def test_every_partition_waiting_is_all_waiting(): ...                # all_waiting True, selected ()
def test_a_partition_over_target_past_the_max_wait_runs_while_written(): ...  # since NOW-61min, written NOW-10s → selected
def test_waiting_until_is_the_max_wait_when_it_comes_first(): ...     # since NOW-59min, written NOW-10s → NOW+1min
def test_an_unknown_last_write_counts_as_quiet(): ...
def test_a_future_last_write_waits_until_the_max_wait(): ...          # written NOW+5min, since NOW → waiting_until NOW+1h; since NOW-1h → selected
def test_zero_quiet_period_never_waits(): ...
def test_zero_max_wait_never_waits(): ...
def test_waiting_partitions_do_not_count_toward_the_cap(): ...        # cap 2: 2 waiting with most reducible + 3 quiet → 2 quiet selected
def test_partitions_of_two_specs_are_selected_together(): ...         # spec 0 and spec 1 both in selected
```

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/service/table/test_track_over_target_partitions.py tests/context/table_maintenance/application/domain/service/table/test_select_compaction_partitions.py tests/context/table_maintenance/application/domain/model/table/test_partition_selection_settings.py -v`. Expected: FAIL, the new names cannot be imported.
- [ ] **Step 3: Implement** the value objects and the two functions. The bound on `partitions_per_job` is a `field_validator`, and `NonNegativeDuration` comes from the `shared` model, as `OperationCooldowns` uses it.
- [ ] **Step 4: Run them and watch them pass.**
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): select the partitions over the target that a compaction job takes (KCL-94)`.

### Task 2: The table keeps its partitions over the target

**Files:**
- Modify: `TM/application/domain/model/table/table.py`; `TM/application/port/outbound/table/tables_repo.py` and `TM/application/port/outbound/table/__init__.py` (re-export `OverTargetPartition`); `TM/adapter/outbound/table/sql/tables_table.py`, `table_row_mapper.py`, `tables_sql_repo.py`; `tests/context/table_maintenance/fakes/in_memory_tables_repo.py`
- Test: `tests/context/table_maintenance/application/domain/model/table/test_table.py`, `tests/context/table_maintenance/adapter/outbound/table/test_tables_sql_repo.py`

**Interfaces:**
- Consumes: `OverTargetPartition` (Task 1).
- Produces:
  - `Table.over_target_partitions: tuple[OverTargetPartition, ...] = ()`.
  - `Table.record_over_target_partitions(partitions: Sequence[OverTargetPartition]) -> bool` replaces the record and returns whether it changed. It returns `False` and changes nothing when the record is equal or the table is dropped, and it does not move `updated_at`.
  - `TablesRepo.record_over_target_partitions(table_id: TableId, partitions: Sequence[OverTargetPartition]) -> bool` (abstract) writes only that column, where the status is not dropped, and returns whether a row was written.
  - Column `Column("over_target_partitions_json", JSON, nullable=True)`, holding `[{"spec_id", "values", "since"}]` (`since` through `IsoDatetimeCodec`); `NULL` reads as `()`. `TableRowMapper.to_values` leaves the key out, so `update` never writes it, and `TablesSqlRepo.create` writes `[]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_recording_over_target_partitions_replaces_them(): ...      # record (eu since T) → True, table.over_target_partitions == (eu,)
def test_recording_the_same_partitions_changes_nothing(): ...       # second call → False
def test_recording_does_not_move_updated_at(): ...
def test_a_dropped_table_records_nothing(): ...                     # mark_dropped then record → False, ()

def test_sql_round_trip_of_over_target_partitions(repo, now):
    repo.create(table)
    entries = (OverTargetPartition(spec_id=0, values=("o'neil", 19700, 1.5, True, None), since=now),)
    assert repo.record_over_target_partitions(table.id, entries) is True
    assert repo.get(table.id).over_target_partitions == entries

def test_update_keeps_the_stored_over_target_partitions(repo, now): ...  # record, then update(an older copy) → still recorded
def test_a_new_table_has_none(repo, now): ...                       # () after create
def test_a_dropped_table_is_not_written(repo, now): ...             # dropped row → False, stays ()
def test_a_null_column_reads_as_none(repo, engine, now): ...        # set column NULL with a raw update → ()
```

Add `record_over_target_partitions` to `InMemoryTablesRepo` with the same rules. It keeps the stored record on `update`, which also closes for this field the "fake does not follow the SQL adapter" gap named in known-follow-ups.

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table/test_table.py tests/context/table_maintenance/adapter/outbound/table/test_tables_sql_repo.py -k "over_target" -v`
- [ ] **Step 3: Implement.** The repo's `update` pops `over_target_partitions_json` from the values, as it already treats `last_committed_at`.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): keep a table's partitions over the compaction target and since when (KCL-94)`.

### Task 3: The assessment selects the partitions

**Files:**
- Modify: `TM/application/domain/model/shared/operation_verdict.py` (`WAITING_FOR_WRITES = "waiting_for_writes"`), `TM/application/domain/model/shared/maintenance_assessment.py` (`over_target_partitions: tuple[OverTargetPartition, ...] = ()`), `TM/application/domain/model/shared/operation_assessment.py` (docstring: `next_eligible_at` is also set for a waiting compaction), `TM/application/domain/service/table/assess_maintenance.py`
- Test: `tests/context/table_maintenance/application/domain/service/table/test_assess_maintenance.py` (the fix wave edits it: read it first), `test_assessment_plan.py`

**Interfaces:**
- Consumes: Task 1 (both functions, `PartitionSelectionSettings`), Task 2 (`Table.over_target_partitions`).
- Produces:
  - `assess_maintenance(table, policy, observation, now, *, cooldowns=DEFAULT_OPERATION_COOLDOWNS, partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS) -> MaintenanceAssessment`.
  - With `per: partition`, `_measure_compaction` does these steps in order:
    1. It finds the qualifying partitions as today.
    2. It tracks them against `table.over_target_partitions`.
    3. It selects with `partition_selection`.
    4. It reports measurements in the order `reducible_files`, `target_file_size`, `qualifying_partitions`, `selected_partitions`, `waiting_partitions`.
    5. It plans `PlannedOperation(partitions=selection.selected)` when the selection is non-empty. That becomes a whole-table `PlannedOperation(operation)` when a selected partition belongs to an unpartitioned spec (the current rule, now applied to the selection).
    6. When `selection.all_waiting`, the verdict is `WAITING_FOR_WRITES` with `next_eligible_at = selection.waiting_until` and nothing is planned.
  - `_assess` sets `DUE` only when the measurement holds and the compaction is not all-waiting. Needs-attention and cooldown then override as today.
  - `MaintenanceAssessment.over_target_partitions` is the tracked tuple: `()` with `per: table`, with no `rewrite_data_files` block, or with nothing over the target.

- [ ] **Step 1: Write the failing tests**

```python
def test_per_partition_plans_only_the_partitions_over_target():
    # partitions eu (reducible 9), us (1), ap (7), at_most 5 → planned partitions (eu, ap); us left out
    ...

def test_the_job_takes_at_most_the_cap():
    a = assess_maintenance(table, policy, observation_with_12_partitions, NOW,
                           partition_selection=PartitionSelectionSettings(partitions_per_job=10,
                               quiet_period=timedelta(minutes=2), max_quiet_wait=timedelta(hours=1)))
    compaction = a.operations[0]
    assert len(compaction.planned.partitions) == 10
    assert _measurement(compaction, "selected_partitions").observed == 10
    assert _measurement(compaction, "qualifying_partitions").observed == 12

def test_all_partitions_under_target_is_not_due(): ...               # NOT_DUE, selected 0, waiting 0, over_target_partitions ()
def test_every_partition_being_written_waits():
    # both over target, last_written_at NOW-30s → verdict WAITING_FOR_WRITES, planned None,
    # next_eligible_at NOW+90s, waiting_partitions 2
    ...

def test_some_waiting_some_selected_is_due(): ...                    # DUE, selected 1, waiting 1
def test_a_partition_over_target_for_an_hour_runs_while_written(): ... # table.over_target_partitions since NOW-61min → selected
def test_waiting_and_cooldown_reads_cooldown(): ...                  # last attempt 10 min ago → COOLDOWN, next_eligible_at = cooldown end
def test_waiting_and_needs_attention_reads_needs_attention(): ...
def test_the_assessment_returns_the_tracked_partitions(): ...        # new eu since NOW; tracked ap keeps its since; us absent
def test_tracking_continues_during_cooldown(): ...                   # COOLDOWN verdict, over_target_partitions still listed
def test_per_table_ignores_quiet_and_the_cap(): ...                  # per table, 12 written-now partitions over → DUE, planned whole table, over_target_partitions ()
def test_no_compaction_block_tracks_nothing(): ...
def test_partitions_of_an_older_spec_are_selected(): ...             # spec 0 and spec 1 over target → planned holds both
def test_a_selected_unpartitioned_partition_plans_the_whole_table(): ... # spec 0 unpartitioned + spec 1 → planned.partitions == ()
```

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/service/table -v`
- [ ] **Step 3: Implement**, then update every existing assess test whose measurement tuple now has the two extra counts.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q`. The plan service still ignores `planned.partitions` here, so its tests are unchanged.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): assess compaction on the partitions over the target, the cap and the quiet period (KCL-94)`.

### Task 4: The plan compacts the selected partitions and records what is over the target

**Files:**
- Modify: `TM/application/service/table/plan_table_maintenance.py`, `TM/application/service/table/get_table_health.py` (constructor kwarg `partition_selection`, passed to `assess_maintenance`), `TM/application/domain/model/table_reconciliation/operation_result.py` (`WAITING_FOR_WRITES = "waiting_for_writes"`), `TM/application/service/table_reconciliation/record_table_reconciliation.py` (`"waiting_for_writes"` in `_RESULT_BY_VERDICT`), `tests/context/table_maintenance/fakes/plan_service_on_fakes.py` (optional `partition_selection`)
- Test: `tests/context/table_maintenance/application/service/table/test_plan_table_maintenance_service.py`, `test_get_table_health.py`, `tests/context/table_maintenance/application/service/table_reconciliation/test_record_table_reconciliation_service.py`, the reconciliation SQL repo test (round trip of the new result)

**Interfaces:**
- Consumes: Task 2 (`Table.record_over_target_partitions`, `TablesRepo.record_over_target_partitions`), Task 3.
- Produces:
  - `PlanTableMaintenanceService(..., *, cooldowns=..., partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS)`. `GetTableHealthService(..., *, cooldowns=..., partition_selection=..., clock=...)`.
  - **Filters.** A planned `rewrite_data_files` with partitions gets `filters` from `build_partition_filters`. Each filter is `PlanTableMaintenanceUseCaseOutput.Filter(spec_id, where)`, sorted by spec id. The plan uses `()` when the builder raises `ValueError` (warning `"cannot scope rewrite_data_files of %s to partitions (%s); compacting the whole table"`) and when any `where` is `""`.
  - **The over-target record.** After a scheduled assessment, before the dry-run check, `table.record_over_target_partitions(assessment.over_target_partitions)` runs. When it reports a change, `self._tables_repo.record_over_target_partitions(table.id, ...)` follows.
  - **The verdict.** `_VERDICTS[OperationVerdict.WAITING_FOR_WRITES] = "waiting_for_writes"`.
  - The docstring of `execute` says what compaction targets now: the selected partitions with `per: partition` on a scheduled plan, else the whole table.

- [ ] **Step 1: Write the failing tests**

```python
def test_due_compaction_targets_the_partitions_over_target(planner, tables_repo, catalog, now):
    _table(tables_repo, now)
    _observe(catalog, now, specs=[{"spec_id": 0, "fields": [_field("region")]}],
             partitions=[_partition(0, ["eu"]), _partition(0, ["us"], files=1), _partition(0, ["o'neil"])])
    compaction = _plan(planner, now).operations[0]
    assert compaction.filters == (
        PlanTableMaintenanceUseCaseOutput.Filter(spec_id=0, where="(`region` = 'eu') OR (`region` = 'o\\'neil')"),
    )

def test_two_specs_give_two_filters(): ...                         # spec 0 eu + spec 1 de → spec_ids (0, 1)
def test_the_plan_takes_at_most_the_cap(): ...                     # partition_selection cap 2, five over target → where holds the 2 with most files
def test_an_unrenderable_partition_compacts_the_whole_table(): ... # source_type "timestamp_ns", transform "day" → filters == (), warning logged (caplog)
def test_per_table_has_no_filters(): ...
def test_a_manual_compaction_has_no_filters(): ...                 # manual ["rewrite_data_files"] on the same table → filters == ()
def test_every_partition_written_now_plans_no_compaction(): ...    # last_written_at now-10s → no operation; check verdict "waiting_for_writes", next_eligible_at now+110s
def test_the_plan_records_the_partitions_over_target(): ...        # tables_repo.get(...).over_target_partitions == (eu since now, o'neil since now)
def test_a_second_plan_keeps_since(): ...                          # plan at now, at now+10min → since stays now
def test_a_dry_run_still_records_them(): ...
def test_a_manual_plan_leaves_them(): ...
def test_a_stale_copy_does_not_overwrite_a_rename(): ...           # rename stored between get and record → stored name kept
def test_health_uses_the_injected_selection(): ...                 # GetTableHealthService with quiet 0 → rewrite verdict "due" for a just-written partition

def test_waiting_for_writes_is_recorded(): ...                     # RecordTableReconciliationService: verdict "waiting_for_writes", no run → result WAITING_FOR_WRITES, next_eligible_at parsed
```

Replace `test_due_compaction_targets_the_whole_table` with `test_due_compaction_targets_the_partitions_over_target`. Keep its `procedure_args` assertion.

- [ ] **Step 2: Run them and watch them fail:** `<pytest> tests/context/table_maintenance/application/service -k "filter or over_target or waiting or cap or since or health" -v`
- [ ] **Step 3: Implement.** Use the R40 fallback shown above. `logger = logging.getLogger(__name__)` is module level.
- [ ] **Step 4: Run them and watch them pass**, then `<pytest> -q` with `tests/architecture`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`; commit `feat(table-maintenance): compact only the partitions over the target and record since when they are (KCL-94)`.

### Task 5: The console reads the new verdict and counts

**Files:**
- Modify: `components/tabs/reconciliationText.ts`, `components/tabs/reconciliationText.test.ts`, `stories/storyData.ts` (one reconciliation whose `rewrite_data_files` result is `waiting_for_writes`, and one started compaction with `selected_partitions` 10 of `qualifying_partitions` 25 and `waiting_partitions` 3)
- Test: `reconciliationText.test.ts`, the `ReconciliationsTab` stories

**Interfaces:**
- Consumes: the record shapes of Task 4. The API types do not change (`result` and `key` are strings), so nothing is regenerated.
- Produces, as exact copy:
  - `RESULT_ORDER` gains `"waiting_for_writes"` right after `"needs_attention"`. `RESULT_LABELS.waiting_for_writes = "Waiting for writes"`.
  - `MEASUREMENT_LABELS.selected_partitions = "Selected partitions"`, `MEASUREMENT_LABELS.waiting_partitions = "Partitions being written"`.
  - `reasonSentence`, `waiting_for_writes`: `` `Due: ${citeAll(met, op)}, but every partition over the target is still being written${when ? `; ${when}` : ""}.` ``, where `when = nextAllowed(op)`.
  - `reasonSentence`, `started` / `would_start` (not manual, `met` non-empty): after `Because …`, when `selected_partitions` is present and less than `qualifying_partitions`, add `` ` This run compacts ${formatCount(selected)} of them` ``, then `` `; ${formatCount(waiting)} ${waiting === 1 ? "is" : "are"} still being written` `` when `waiting_partitions > 0`, then `"."`.

- [ ] **Step 1: Write the failing tests**

```ts
it("says a compaction waits for writes", () => {
  expect(reasonSentence(op("waiting_for_writes", [REDUCIBLE_MET, context("qualifying_partitions", 2)], "2026-11-20T12:05:00Z")))
    .toBe("Due: reducible files 1,240 across 2 partitions (needs > 5 per partition), but every partition over the target is still being written; next allowed Nov 20, 12:05.");
});
it("says how many partitions a capped run compacts", () => {
  const ms = [REDUCIBLE_MET, context("qualifying_partitions", 25), context("selected_partitions", 10), context("waiting_partitions", 3)];
  expect(reasonSentence(op("started", ms))).toBe(
    "Because reducible files 1,240 across 25 partitions (needs > 5 per partition). This run compacts 10 of them; 3 are still being written.");
});
it("adds nothing when the run takes every partition over the target", () => { /* selected == qualifying */ });
it("labels the new result and counts", () => { /* resultLabel, measurementLabel */ });
```

Each expected string comes from the helpers the test file already has, built with the numbers given; adjust the test's `REDUCIBLE_MET` value to match.

- [ ] **Step 2: Run and watch them fail:** `<vitest> reconciliationText`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** `<vitest>`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`; commit `feat(console): explain compaction waiting for writes and capped partition runs (KCL-94)`.

### Task 6: The three settings, their wiring and the Platform settings page

**Files:**
- Create: `bootstrap/container/build_partition_selection_settings.py` (export from `bootstrap/container/__init__.py`)
- Modify: `bootstrap/configs/app_settings.py`; `bootstrap/container/build_use_cases.py`, `build_connected_use_cases.py`, `build_platform_settings.py`; `TM/application/domain/model/shared/platform_settings.py`; `TM/application/service/table_maintenance_run/get_platform_settings.py`; `platform/25-lakehouse-control-plane/chart/values.yaml`, `chart/templates/configmap.yaml`; `src/data-platform/frontend/src/stories/storyData.ts` (the fifth group); `pages/PlatformSettingsPage.test.tsx` if it counts groups
- Test: `tests/bootstrap/configs/test_app_settings.py`, new `tests/bootstrap/container/test_build_partition_selection_settings.py`, `test_build_platform_settings.py`, `test_build_use_cases.py`, `test_build_connected_use_cases.py`, `tests/context/table_maintenance/application/service/table_maintenance_run/test_get_platform_settings.py`, `tests/context/table_maintenance/adapter/inbound/web/table_maintenance_run/test_platform_settings_route.py`

**Interfaces:**
- Consumes: `PartitionSelectionSettings` (Task 1), the service kwargs (Task 4).
- Produces:
  - `AppSettings.maintenance_compaction_partitions_per_job: int = Field(default=10, ge=1, le=1000)`, `maintenance_compaction_quiet_seconds: int = Field(default=120, ge=0)`, `maintenance_compaction_max_quiet_wait_seconds: int = Field(default=3600, ge=0)`.
  - `build_partition_selection_settings(settings: AppSettings) -> PartitionSelectionSettings`. `build_use_cases(..., partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS)` passes it to the plan and health services. `build_connected_use_cases` passes `build_partition_selection_settings(settings)`.
  - `PlatformSettings` gains `compaction_partitions_per_job`, `compaction_quiet_seconds` and `compaction_max_quiet_wait_seconds` (ints). `GetPlatformSettingsService` returns five groups, with `partition_selection` as in Global Constraints. The OpenAPI document does not change: the response is generic.
  - Chart: `worker.compactionPartitionsPerJob: 10`, `worker.compactionQuietSeconds: 120`, `worker.compactionMaxQuietWaitSeconds: 3600`, rendered into the three `GLAC_MAINTENANCE_COMPACTION_*` vars in `table-maintenance-config`.

- [ ] **Step 1: Write the failing tests**

```python
def test_app_settings_read_the_partition_selection_env(monkeypatch): ...   # PER_JOB=4, QUIET=0, MAX_QUIET_WAIT=600 → 4, 0, 600
@pytest.mark.parametrize("value", ["0", "1001"])
def test_partitions_per_job_out_of_range_is_refused(monkeypatch, value): ...  # ValidationError
def test_negative_quiet_is_refused(monkeypatch): ...
def test_build_partition_selection_settings(): ...                         # → PartitionSelectionSettings(4, 0 s, 600 s)
def test_platform_settings_list_partition_selection():
    groups = GetPlatformSettingsService(settings).execute(GetPlatformSettingsUseCaseInput()).groups
    assert [g.key for g in groups] == ["execution_capacity", "compute_sizes", "cooldown_and_backoff",
                                       "partition_selection", "discovery"]
    assert [(i.key, i.value, i.unit) for i in groups[3].items] == [
        ("maintenance_compaction_partitions_per_job", 10, "partitions"),
        ("maintenance_compaction_quiet_seconds", 120, "seconds"),
        ("maintenance_compaction_max_quiet_wait_seconds", 3600, "seconds"),
    ]
def test_connected_use_cases_get_the_settings(): ...                       # the plan service built from AppSettings(quiet 0) plans a just-written partition
```

If the fix wave has changed the group list, keep its groups and insert `partition_selection` before `discovery`.

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/bootstrap tests/context/table_maintenance/application/service/table_maintenance_run/test_get_platform_settings.py -k "partition_selection or platform_settings" -v`
- [ ] **Step 3: Implement**, then update `storyData.ts` to the five groups.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`; `<vitest> PlatformSettingsPage`. Then `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c "GLAC_MAINTENANCE_COMPACTION_"` prints `3`.
- [ ] **Step 5: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): make compaction partition selection platform settings (KCL-94)`.

### Task 7: A run records the `where` clauses it compacts with (backend)

**Files:**
- Modify: `TM/application/domain/model/table_maintenance_run/operation_run.py`, `table_maintenance_run.py`; `TM/application/port/inbound/table_maintenance_run/create_table_maintenance_run/input.py`; `TM/application/service/table_maintenance_run/create_table_maintenance_run.py`, `table_maintenance_run_output_fields.py`; `TM/application/port/outbound/table_maintenance_run/__init__.py` (re-export `SpecFilter`); `TM/adapter/outbound/table_maintenance_run/sql/table_maintenance_run_row_mapper.py`; `TEMPORAL/inbound/workflows/table_maintenance_workflow.py`; `TM/adapter/inbound/web/table_maintenance_run/dto.py`; `openapi.json` and the generated client (`task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`)
- Test: `tests/.../domain/model/table_maintenance_run/test_table_maintenance_run.py`, `test_operation_run.py`; `tests/.../service/table_maintenance_run/test_table_maintenance_run_services.py`; `tests/.../adapter/outbound/table_maintenance_run/test_table_maintenance_runs_sql_repo.py`; `tests/.../temporal/inbound/test_table_maintenance_workflow.py`, `test_run_activity_payloads.py`; `tests/.../web/table_maintenance_run/test_table_maintenance_run_routes.py`

**Interfaces:**
- Consumes: the plan output `filters` (Task 4).
- Produces:
  - `OperationRun.filters: tuple[SpecFilter, ...] = ()`. `TableMaintenanceRun.create(..., filters: Mapping[MaintenanceOperation, Sequence[SpecFilter]] | None = None)`. Filters are refused with `InvalidRunTransition` for an operation other than `REWRITE_DATA_FILES`, or for one not in the run.
  - `CreateTableMaintenanceRunUseCaseInput.Filter(spec_id: int, where: str)` and `filters: dict[str, tuple[Filter, ...]] = Field(default_factory=dict)`, keyed by operation name. An unknown operation name raises `ValidationError`.
  - The workflow adds `"filters": {op["operation"]: op["filters"] for op in operations if op["filters"]}` to the `CREATE_MAINTENANCE_RUN` payload. The submit payload is unchanged.
  - The run's `operations_json` entry gains `"filters": [{"spec_id", "where"}]`; a missing key reads as `()`. `table_maintenance_run_output_fields` adds `"filters"` with the same shape.
  - `TableMaintenanceRunFilterApiResponse(spec_id: int, where: str)`; `TableMaintenanceRunOperationApiResponse.filters: list[TableMaintenanceRunFilterApiResponse] = Field(description="The where clauses each job of this operation passes to rewrite_data_files, one per partition spec; empty: the whole table.")`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_run_keeps_the_compaction_filters():
    run = TableMaintenanceRun.create(RUN_ID, TABLE_ID, TriggerType.SCHEDULED, [REWRITE, EXPIRE], NOW,
                                     execution_ref="wf", filters={REWRITE: [SpecFilter(spec_id=0, where="(`region` = 'eu')")]})
    assert run.operations[0].filters == (SpecFilter(spec_id=0, where="(`region` = 'eu')"),)
    assert run.operations[1].filters == ()

def test_filters_on_another_operation_are_refused(): ...          # {EXPIRE: [...]} → InvalidRunTransition
def test_filters_for_an_operation_not_in_the_run_are_refused(): ...
def test_create_run_service_saves_the_filters(): ...              # input filters {"rewrite_data_files": ({"spec_id": 0, "where": "x"},)} → stored
def test_create_run_service_refuses_an_unknown_operation_key(): ...  # {"compact": ...} → ValidationError
def test_sql_round_trip_keeps_the_filters(): ...
def test_a_stored_operation_without_filters_reads_none(): ...     # operations_json entry without "filters" → ()
def test_the_workflow_creates_the_run_with_the_plans_filters(): ...  # h.fakes.created[0]["filters"] == {"rewrite_data_files": [{"spec_id": 0, "where": "rewrite_data_files = 1"}]} for a plan of rewrite_data_files only
def test_the_workflow_sends_no_filters_for_a_whole_table_plan(): ...  # plan filters [] → created[0]["filters"] == {}
def test_get_run_shows_the_filters(client): ...                   # body["operations"][0]["filters"] == [{"spec_id": 0, "where": "..."}]
def test_get_run_shows_empty_filters_for_the_whole_table(client): ...
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "filters" -v`
- [ ] **Step 3: Implement**, then run `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`, including `tests/architecture/test_temporal_workflow_determinism.py`, `test_inbound_port_field_types.py` and `test_dto_naming.py`. Do not commit yet: the console must compile against the new client (Task 8).

### Task 8: The console shows what a compaction compacted

**Files:**
- Create: `lib/compactionScopeText.ts`, `lib/compactionScopeText.test.ts`
- Modify: `components/tabs/MaintenanceTab.tsx`, `components/tabs/MaintenanceTab.test.tsx`; `test/fixtures.ts`, `stories/storyData.ts`, `lib/anyRunInFlight.test.ts` (every maintenance-run operation fixture gets `filters`); the `TablePage` / Maintenance stories (one run whose compaction has two filters, one long `where` of 10 partitions, and one whole-table manual run)

**Interfaces:**
- Consumes: the generated `TableMaintenanceRunOperationApiResponse.filters` (Task 7).
- Produces:
  - `compactionScopeText(op: TableMaintenanceRunOperationApiResponse): {summary: string; wheres: {specId: number; where: string}[]} | null`. It returns `null` for every operation other than `rewrite_data_files`. Empty `filters` gives `{summary: "Whole table", wheres: []}`; otherwise `{summary: "Partitions over the target", wheres: [...] }`.
  - `OperationDetail` adds, under its header row, `<p className="type-body-small">Scope: {summary}</p>`. For each where it adds an item in a `<ul className="type-code text-on-surface-variant">`, rendered `spec {specId}: {where}`, with `break-all` so a long clause wraps (no horizontal page scroll at phone width).

- [ ] **Step 1: Write the failing tests and stories:**
  - `compactionScopeText` covers its three cases: another operation, the whole table, and two specs.
  - `MaintenanceTab`: an expanded run shows "Scope: Partitions over the target" and `spec 0: (\`region\` = 'eu')`, and a manual run shows "Scope: Whole table".
  - Stories: the phone-width Maintenance story with the 10-partition `where` passes `expectNoHorizontalPageScroll`.
- [ ] **Step 2: Run and watch them fail:** `<vitest> compactionScopeText MaintenanceTab`
- [ ] **Step 3: Implement** with design-system parts only (`src/data-platform/frontend/CLAUDE.md`).
- [ ] **Step 4: Run and watch them pass:** `<vitest>`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories`.
- [ ] **Step 5: Gate and commit Tasks 7 and 8 together.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `feat(table-maintenance): record and show the where clauses a compaction run passes (KCL-94)` with the backend, `openapi.json`, the generated client and the console.

### Task 9: e2e script and documentation

**Files:**
- Modify: `platform/25-lakehouse-control-plane/e2e.sh`, `platform/25-lakehouse-control-plane/README.md`, `src/data-platform/backend/CLAUDE.md`, `src/data-platform/frontend/CLAUDE.md` (Maintenance tab line, if the tab is described), `docs/agents/known-follow-ups.md`, `docs/agents/project-history.md`

**Interfaces:**
- Consumes: the run API `filters` (Task 7) and the settings (Task 6).

- [ ] **Step 1: e2e.** Read `e2e.sh` at HEAD first, since the fix wave edits it.
  - Add `assert_partition_compaction run_id…`. For each run, `GET /v1/table-maintenance-runs/{id}` must have exactly one `rewrite_data_files` operation whose `filters` are non-empty with no empty `where`, and print each `where` with `progress`. Across the runs, at least one `where` must hold the escaped quote `'o\'neil'` (the check of the pre-KCL-93 `assert_partition_filter`).
  - Use it for `${REGIONS_RUNS}` in place of `assert_whole_table_compaction`.
  - `assert_whole_table_compaction` now reads the run API: `filters == []` for `rewrite_data_files`. It keeps being used for `${ORDERS_MANUAL_RUN_ID}`.
  - The `tm-e2e-regions` description becomes "e2e: scheduled per-partition compaction".
  - After the regions run, print (no assertion, since timing decides it) the results of `rewrite_data_files` in the regions reconciliations, so a `waiting_for_writes` shows in the log.
  - Run `uv run --directory /Users/kcl/Projects/retail-lakehouse pre-commit run shellcheck --all-files`.
- [ ] **Step 2: Docs.**
  - README:
    - Replace "`per: partition` decides only whether compaction is due; a run compacts the whole table either way" with one paragraph on the scheduled selection, the cap, the quiet period, the maximum wait, `waiting_for_writes`, the manual whole-table run and the run's `filters`.
    - The platform settings paragraph: five groups, and the three chart keys with defaults and env names.
    - e2e step: regions compacted per partition with the escaped quote checked.
  - Backend `CLAUDE.md`: a short paragraph after the policy paragraph covering the over-target record on `Table` with its narrow write, the two pure functions, the new verdict and result, and `OperationRun.filters`.
  - `known-follow-ups.md`:
    - Remove the two entries "`assess_maintenance` still selects the qualifying partitions … until KCL-94" and "`per: partition` decides only whether compaction is due … until KCL-94".
    - Add (2026-11-20, KCL-94):
      - Left-over and waiting partitions wait for the next check that `on:` and the rewrite cooldown allow: a table with 100 partitions over the target and the default cap takes ten cooldowns. There is no recheck timer.
      - The over-target record grows with the number of partitions over the target; it is one JSON column on the table row.
      - `per: table` ignores the quiet period, so it can compact a partition still being written.
      - A manual compaction always rewrites the whole table.
  - `project-history.md`: one 2026-11-20 KCL-94 line naming the three env vars and chart keys with their defaults, the verdict and result `waiting_for_writes`, the measurements `selected_partitions` and `waiting_partitions`, `Table.over_target_partitions`, and `filters` on each run operation in the API. It ends with "No migration: rebuild the cluster."
- [ ] **Step 3: Gate and commit.** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`; commit `docs(table-maintenance): describe partition-selected compaction and check it in the e2e (KCL-94)`.

### Task 10: Verify on a rebuilt cluster (controller, batched with KCL-91 and KCL-95)

The controller runs this in the batched rebuild; it does not run per issue. The temporary values below are never committed.

- [ ] **Step 1: Rebuild.** `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse onboard KUBE_CONTEXT=retail-lakehouse`. Then `task -d /Users/kcl/Projects/retail-lakehouse apps:validate KUBE_CONTEXT=retail-lakehouse` must exit 0.
- [ ] **Step 2: Settings.** `GET /v1/platform-settings` has group `partition_selection` with 10, 120 and 3600, between `cooldown_and_backoff` and `discovery`. The console's Platform settings page shows "Compaction partition selection" with "10 partitions", "2 min" and "1 h".
- [ ] **Step 3: Lower two values for the test.**
  - Set them in `values.yaml`: `worker.rewriteDataFilesCooldownSeconds: 60` and `worker.compactionMaxQuietWaitSeconds: 600`.
  - Rerun `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/bootstrap.sh`, never `kubectl patch configmap`.
  - Create the namespace `iceberg.kcl94` and a discovery rule, or after KCL-71 a discovery policy, that manages `iceberg / kcl94 / *`.
  - Attach a policy `kcl94` to the namespace: `on: {schedule: {every_seconds: 300}, catalog_commit: {debounce_seconds: 60}}`, `rewrite_data_files: {target: {reducible_files: {at_most: 1}, per: partition}, options: {min_input_files: 2}}` and no other block. The option is needed because Iceberg's default `min-input-files` is 5, and a 3-file partition would stay over the target forever.
- [ ] **Step 4: Cap and order.**
  - Create `iceberg.kcl94.capped` (`region VARCHAR, id BIGINT`, partitioned by `region`).
  - In one `trino_sql` call, insert `n + 1` single-row commits into `r01` … `r12` (region `rNN` gets `NN + 1` rows), so `rNN` has `NN` reducible files and `r01` is not over the target.
  - After the quiet period, the first compaction run's `filters` holds one `where` naming `r03` … `r12` and neither `r01` nor `r02`. Its reconciliation shows `qualifying_partitions` 11 and `selected_partitions` 10.
  - The run succeeds, and `capped$files` drops for those ten partitions.
  - The next check after the 60 s cooldown compacts `r02` alone.
- [ ] **Step 5: Quiet period and maximum wait.**
  - Create `iceberg.kcl94.hot` (partitioned by `region`) and insert 4 single-row commits into `cold`.
  - The commit-window check about 60 s later records `rewrite_data_files` `waiting_for_writes`, with `next_eligible_at` about 120 s after the last write, and starts no run.
  - Right after that record, insert 3 rows into `hot`, so it is over the target. Then keep inserting one row into `hot` every 30 s for 15 minutes.
  - The next check, more than 120 s after the last `cold` write, starts a run that compacts `cold` only: its `where` names `cold` and not `hot`, and its reconciliation shows `selected_partitions` 1 and `waiting_partitions` 1.
  - About 600 s after `hot` first went over the target, a run compacts `hot` while the writes go on: its `where` names `hot`.
  - Every run succeeds, with no commit conflict failure.
- [ ] **Step 6: Transforms and spec evolution.**
  - Create `iceberg.kcl94.events` (`id BIGINT, ts TIMESTAMP(6) WITH TIME ZONE`, partitioned by `ARRAY['day(ts)', 'bucket(id, 4)']`) and insert 3 single-row commits for each of two days and two buckets.
  - Then `ALTER TABLE iceberg.kcl94.events SET PROPERTIES partitioning = ARRAY['day(ts)']` and insert 3 more rows for one day.
  - The next compaction run has two `filters` (spec 0 with `system.days` and `system.bucket` terms, spec 1 with `system.days`), its driver log shows two `CALL`s, and it succeeds.
- [ ] **Step 7: Manual run and console.**
  - A manual `rewrite_data_files` on `kcl94.capped` records `filters: []`.
  - In the console's Maintenance tab, the runs above read "Scope: Partitions over the target" with their `spec N: …` lines, and the manual run reads "Scope: Whole table". At phone width the long `where` wraps with no horizontal page scroll.
  - The Reconciliations tab reads "Waiting for writes" with its sentence for the Step 5 check, and "This run compacts 10 of them." for the Step 4 run.
- [ ] **Step 8: Restore and finish.**
  - Restore `values.yaml` with `git -C /Users/kcl/Projects/retail-lakehouse checkout -- platform/25-lakehouse-control-plane/chart/values.yaml`, then rerun `bootstrap.sh`.
  - `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` must pass, with the regions run's `where` holding `'o\'neil'`.
  - Then run `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`. Record the results on KCL-94 in a dated comment, and push only when the user asks.
