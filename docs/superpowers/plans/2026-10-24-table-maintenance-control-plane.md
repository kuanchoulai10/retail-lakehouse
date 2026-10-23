# Table Maintenance Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Airflow-style table-maintenance backend with a Temporal-based control plane that discovers Iceberg tables, reconciles each one in its own workflow, runs the four maintenance procedures on Spark, and is deployed by a Helm chart in wave `25-lakehouse-control-plane`.

**Architecture:** Clean Architecture in `src/table-maintenance/backend` (domain → application → adapters → bootstrap). Temporal workflows and activities are inbound adapters that call use cases; PyIceberg, SQLAlchemy, Kubernetes and the Temporal client are outbound adapters behind ports. One image, four components (`api`, `worker`, `event_consumer`, `migrate`); Spark runtime image in `src/table-maintenance/runtime/spark`.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2 (Postgres / SQLite in tests), PyIceberg + PyArrow, `temporalio`, a Kafka client (see Task 16), `kubernetes`, Spark 4.0 + Iceberg 1.10.1, Helm.

**Spec:** `docs/superpowers/specs/2026-10-24-table-maintenance-control-plane-design.md` — read it before any task; it is the source of truth for behaviour.

## Global Constraints

- Backend root `BE = src/table-maintenance/backend`. Run tools as `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend <tool>`; below, `$UV` stands for that prefix.
- Every commit passes `$UV pytest -q`, `$UV ty check`, `$UV ruff check .`, `$UV lint-imports`, plus the repo pre-commit hooks. TDD: failing test first.
- `CLAUDE.md` code style: one exported object per file, filename = export name, `__init__.py` re-exports, intra-package direct imports, `abc.ABC` (no `Protocol`), `StrEnum`, `from __future__ import annotations` everywhere, domain = dataclasses only (no Pydantic).
- Naming: repos `{Aggregate}Repo` (existing style is plural, e.g. `ManagedTablesRepo`); gateways `{Verb}{Noun}Gateway` with verbs from `Read, Submit, Send, Publish, Poll, Sync, Write, Delete, Update`; DTO suffixes `UseCaseInput/UseCaseOutput/GatewayInput/GatewayOutput/ApiRequest/ApiResponse`; gateway input/output primitive-only.
- Inbound port layout `application/port/inbound/{group}/{verb_noun}/{__init__,input,output,use_case}.py`; services `application/service/{group}/{verb_noun}.py` class `{VerbNoun}Service` implementing the use case.
- Namespaces: control plane `lakehouse-control-plane`, Spark `lakehouse-maintenance-operations`, Temporal `temporal` (frontend `temporal-frontend.temporal.svc.cluster.local:7233`, Temporal namespace `default`).
- Kubernetes scripts: `KUBE_CONTEXT` required, `kubectl <verb> ... --namespace X --context "${KUBE_CONTEXT}"`, no `cd`, no yaml comments, all images pinned, source `scripts/utils/log.sh` and never override its EXIT trap.
- Commits on `main`, conventional (`feat(table-maintenance): ...`), header and body lines ≤ 100 chars, ending with the session attribution line.
- Spec values: reconcile interval 1 h; discovery every 10 min; global Spark capacity 2; 3 attempts in total per operation; failure backoff doubles the cooldown per consecutive failure, cap 24 h; `remove_orphan_files.older_than` ≥ 1 day, default interval 7 days; default target file size 512 MiB (`536870912`); operation order compaction → manifests → expire snapshots → orphan files; no default discovery rules.

## Review Focus

1. **Unpartitioned tables and evolved specs** — an unpartitioned table (or a spec with only `void` fields) must compact as a whole table, never produce an empty/invalid `where`; files in old specs must not break the predicate builder. Tests: Task 4 `test_unpartitioned_table_plans_whole_table`, Task 5 `test_void_fields_are_skipped` and `test_one_filter_per_spec_id`.
2. **Capacity slot leak** — a `MaintenanceWorkflow` that is terminated or times out while holding a slot must not block the system forever. Test: Task 13 `test_capacity_lease_expires_when_holder_never_releases`.
3. **Duplicate, late, or stale Spark callbacks** — a callback for an old attempt, a second callback, or a callback for an unknown run must not corrupt the run record or crash the API. Tests: Task 13 `test_stale_attempt_callback_is_ignored`, Task 15 `test_callback_for_unknown_run_returns_404`.
4. **Table dropped or renamed mid-run** — the Spark job fails, the operation is recorded `FAILED`, discovery later marks the table `DROPPED` and the reconcile workflow ends without a retry storm. Test: Task 14 `test_dropped_signal_ends_workflow_after_in_flight_run`.
5. **Event noise and malformed events** — maintenance's own commits and CDC commits emit `AFTER_UPDATE_TABLE` continuously; unknown or malformed JSON events and multi-level namespaces (`["a","b"]`) must be handled without crashing or re-triggering maintenance in a loop. Tests: Task 16 `test_malformed_event_is_skipped`, `test_multi_level_namespace_joined_with_dot`; Task 9 `test_table_hint_for_registered_table_signals_but_cooldown_blocks_replan`.

---

## Shared vocabulary (decided here, used by every task)

| Name | Kind | Location (under `BE`) | Definition |
|---|---|---|---|
| `MaintenanceOperation` | StrEnum | `application/domain/model/maintenance/maintenance_operation.py` | `REWRITE_DATA_FILES="rewrite_data_files"`, `REWRITE_MANIFESTS="rewrite_manifests"`, `EXPIRE_SNAPSHOTS="expire_snapshots"`, `REMOVE_ORPHAN_FILES="remove_orphan_files"`; class method `ordered() -> tuple[MaintenanceOperation, ...]` in that order |
| `TableName` | VO | `application/domain/model/managed_table/table_name.py` | `catalog: str`, `namespace: str` (levels joined with `.`), `table: str`; `qualified() -> str` = `"{namespace}.{table}"` |
| `TableUuid` | EntityId | `.../managed_table/table_uuid.py` | Iceberg `table-uuid` string |
| Workflow IDs | constants | `application/domain/model/maintenance/workflow_ids.py` | `table_reconcile_workflow_id(uuid) = f"table-reconcile-{uuid}"`, `maintenance_workflow_id(run_id) = f"maintenance-{run_id}"`, `CAPACITY_WORKFLOW_ID = "maintenance-capacity"`, `DISCOVERY_SCHEDULE_ID = "table-discovery"` |
| Signals | constants | same file | `SIGNAL_SETTINGS_CHANGED="settings_changed"`, `SIGNAL_TABLE_UPDATED="table_updated"`, `SIGNAL_TRIGGER_NOW="trigger_now"`, `SIGNAL_PAUSE="pause"`, `SIGNAL_RESUME="resume"`, `SIGNAL_STOP="stop"`, `SIGNAL_MAINTENANCE_FINISHED="maintenance_finished"`, `SIGNAL_OPERATION_RESULT="operation_result"`, `SIGNAL_CAPACITY_ACQUIRE="acquire"`, `SIGNAL_CAPACITY_RELEASE="release"`, `SIGNAL_CAPACITY_GRANTED="capacity_granted"` |
| Task queue | constant | same file | `TASK_QUEUE = "table-maintenance"` |
| Spark catalog alias | rule | — | Spark registers each Polaris catalog under its own name, so SQL uses `TableName.catalog` directly (e.g. `iceberg.system.bucket(...)`) |

---

### Task 1: Reset the backend to a clean skeleton

**Files:**
- Delete: everything under `BE/application/domain/model/{catalog,job,job_run}`, `outbox_entry.py`, `BE/application/port/{inbound,outbound}/*`, `BE/application/service/*`, `BE/adapter/inbound/{web,scheduler,messaging}`, `BE/adapter/outbound/{catalog,job,job_run}`, `BE/adapter/outbound/sql/{event_outbox_sql_store.py,outbox_table.py}`, `BE/bootstrap/{scheduler.py,messaging.py}`, old `bootstrap/configs/*_adapter.py`, `scheduler_settings.py`, `messaging_settings.py`, `k8s_settings.py`, and their tests (`BE/tests/{application,adapter,bootstrap}`, `BE/tests/test_*.py`). Keep `base/` + `tests/base/` + `tests/architecture/`.
- Modify: `BE/pyproject.toml`, `BE/.importlinter`, `BE/bootstrap/configs/component.py`, `BE/entrypoint.py`, `BE/tests/architecture/*.py`
- Create: `application/domain/model/maintenance/{maintenance_operation.py,workflow_ids.py}`, `application/domain/model/managed_table/{table_name.py,table_uuid.py}` (shared vocabulary)

**Interfaces:**
- Produces: shared vocabulary above; `Component` StrEnum `API="api"`, `WORKER="worker"`, `EVENT_CONSUMER="event_consumer"`, `MIGRATE="migrate"`; `entrypoint.main()` dispatching to `bootstrap.api`, `bootstrap.worker`, `bootstrap.event_consumer`, `bootstrap.migrate` (each `main()`; stubs raising `NotImplementedError` until Task 17).

- [ ] **Step 1:** Delete the old model, ports, services, adapters, bootstrap modules and their tests listed above. Remove `croniter`; add `temporalio` and `pyarrow` (verify `uv lock` resolves wheels for Python 3.14; if `temporalio` has no 3.14-compatible wheel, lower `requires-python` and the Dockerfile base image to the newest supported version and note it in the commit body).
- [ ] **Step 2: Update architecture tests.** In `test_inbound_port_structure.py` set `AGGREGATE_GROUPS = ["discovery", "discovery_rule", "managed_table", "maintenance_run", "policy_template", "reconcile"]`, `AGGREGATE_GROUPS_NO_INPUT = set()`. In `test_outbound_port_structure.py` set `AGGREGATE_GROUPS = ["catalog", "discovery", "discovery_rule", "managed_table", "maintenance_run", "policy_template", "spark", "workflow"]`. In `test_directory_structure.py` require `adapter/inbound/{web,temporal,event_consumer}` and `adapter/outbound`. In `test_service_structure.py` add verbs `Register`, `Include`, `Exclude`, `Reset`, `Plan`, `Record`. Allow empty groups (a group dir with only `__init__.py`) so the skeleton passes.
- [ ] **Step 3: Update `.importlinter`.** Replace `adapter.inbound.scheduler/messaging` with `adapter.inbound.temporal` and `adapter.inbound.event_consumer`; add `temporalio`, `pyiceberg`, `pyarrow`, `sqlalchemy` to every `forbidden_modules` list that already forbids `fastapi`/`kubernetes` for `application.*`; layers contract top layer becomes `adapter.inbound` (web, temporal, event_consumer as independent siblings).
- [ ] **Step 4: Write `tests/application/domain/model/test_shared_vocabulary.py`:** `MaintenanceOperation.ordered()` returns the four values in spec order; `table_reconcile_workflow_id("u1") == "table-reconcile-u1"`; `TableName("iceberg", "a.b", "t").qualified() == "a.b.t"`; `TableName` rejects empty `table` (raises `ValueError`).
- [ ] **Step 5:** Run `$UV pytest -q` → new test FAILS; implement the vocabulary; run all checks → PASS.
- [ ] **Step 6: Commit** `refactor(table-maintenance): reset backend for temporal control plane`.

### Task 2: Domain — maintenance settings, policy templates, discovery rules

**Files:**
- Create `application/domain/model/maintenance_settings/`: `maintenance_settings.py`, `rewrite_data_files_settings.py`, `rewrite_manifests_settings.py`, `expire_snapshots_settings.py`, `remove_orphan_files_settings.py`, `compaction_scope.py`, `invalid_maintenance_settings.py` (exception)
- Create `application/domain/model/policy_template/`: `policy_template.py`, `policy_template_id.py`
- Create `application/domain/model/discovery_rule/`: `discovery_rule.py`, `discovery_rule_id.py`, `rule_effect.py`, `table_pattern.py`, `invalid_discovery_rule.py`
- Create `application/domain/model/discovery/discovery_settings.py`, `discovery_settings_id.py`
- Create `application/domain/service/match_discovery_rule.py`
- Test: `tests/application/domain/model/{maintenance_settings,policy_template,discovery_rule,discovery}/`, `tests/application/domain/service/test_match_discovery_rule.py`

**Interfaces:**
- Produces (frozen VOs, `timedelta` durations):
  - `RewriteDataFilesSettings(enabled=True, min_interval=1h, scope=CompactionScope.PARTITION, target_file_size_bytes: int | None = None, min_reducible_files: int = 5)`; `CompactionScope` = `PARTITION`/`TABLE`.
  - `RewriteManifestsSettings(enabled=True, min_interval=6h, min_small_manifests: int = 5, small_manifest_bytes: int | None = None)` (None → table property `commit.manifest.target-size-bytes`, else 8 MiB).
  - `ExpireSnapshotsSettings(enabled=True, min_interval=6h, older_than=1d, retain_last: int = 10)`.
  - `RemoveOrphanFilesSettings(enabled=True, min_interval=7d, older_than=3d)`.
  - `MaintenanceSettings(reconcile_interval=1h, rewrite_data_files=..., rewrite_manifests=..., expire_snapshots=..., remove_orphan_files=...)`; `for_operation(op) -> <settings>`; `min_interval(op) -> timedelta`; `enabled(op) -> bool`.
  - `PolicyTemplate(AggregateRoot[PolicyTemplateId])`: `name: str`, `settings: MaintenanceSettings`, `created_at`, `updated_at`; `create(...)`, `rename(name, now)`, `update_settings(settings, now)`.
  - `TablePattern(catalog: str = "*", namespace: str = "*", table: str = "*")`; `matches(name: TableName) -> bool` using `fnmatch.fnmatchcase` on each part.
  - `DiscoveryRule(AggregateRoot[DiscoveryRuleId])`: `priority: int`, `effect: RuleEffect` (`INCLUDE`/`EXCLUDE`), `pattern: TablePattern`, `template_id: PolicyTemplateId | None`, `enabled: bool`, timestamps; `create(...)`, `update(...)`.
  - `DiscoverySettings(AggregateRoot[DiscoverySettingsId])` singleton id `"global"`, `enabled: bool = True`; `enable()`, `disable()`.
  - `match_discovery_rule(rules: Sequence[DiscoveryRule], name: TableName) -> DiscoveryRule | None`.

- [ ] **Step 1: Write failing tests** (one file per object), including:
  - `test_remove_orphan_files_older_than_below_one_day_rejected`: `RemoveOrphanFilesSettings(older_than=timedelta(hours=23))` raises `InvalidMaintenanceSettings`.
  - `test_non_positive_intervals_rejected`: zero `reconcile_interval`, zero `min_interval`, `retain_last=0`, `min_reducible_files=0`, `target_file_size_bytes=0` each raise `InvalidMaintenanceSettings`.
  - `test_include_rule_requires_template`: `DiscoveryRule.create(effect=INCLUDE, template_id=None, ...)` raises `InvalidDiscoveryRule`; `EXCLUDE` with a template also raises.
  - `test_pattern_matches_globs`: `TablePattern("iceberg", "sales*", "*_raw").matches(TableName("iceberg","sales_eu","orders_raw"))` is True; namespace `"inventory"` is False; matching is case-sensitive.
  - `test_first_matching_rule_by_priority_wins`: rules (priority 10 EXCLUDE `*.tmp_*`), (priority 20 INCLUDE `*`) → `tmp_x` matches the EXCLUDE rule; `orders` matches the INCLUDE rule.
  - `test_disabled_rules_are_ignored` and `test_no_rules_returns_none`.
  - `test_equal_priority_tie_broken_by_rule_id`: lower `DiscoveryRuleId.value` (string order) wins.
- [ ] **Step 2:** Run tests → FAIL (import errors).
- [ ] **Step 3:** Implement. Validation in `__post_init__`.
- [ ] **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add maintenance settings, templates and discovery rules`.

### Task 3: Domain — managed table aggregate

**Files:**
- Create `application/domain/model/managed_table/`: `managed_table.py`, `table_status.py`, `table_selection.py`, `operation_state.py`, `invalid_table_transition.py`
- Test: `tests/application/domain/model/managed_table/`

**Interfaces:**
- Consumes: `TableUuid`, `TableName`, `MaintenanceSettings`, `MaintenanceOperation`, `DiscoveryRuleId`, `PolicyTemplateId`.
- Produces:
  - `TableStatus` = `ACTIVE`, `PAUSED`, `EXCLUDED`, `DROPPED`; `TableSelection` = `AUTO`, `MANUAL`.
  - `OperationState(last_attempt_at: datetime | None = None, consecutive_failures: int = 0)`; `effective_cooldown(base: timedelta, cap: timedelta = timedelta(hours=24)) -> timedelta` = `min(base * 2**consecutive_failures, cap)` (but never below `base`); `after_success(at) -> OperationState`; `after_failure(at) -> OperationState`.
  - `ManagedTable(AggregateRoot[TableUuid])` fields: `name`, `status`, `selection`, `settings: MaintenanceSettings | None`, `matched_rule_id: DiscoveryRuleId | None`, `source_template_id: PolicyTemplateId | None`, `operation_states: dict[MaintenanceOperation, OperationState]`, `registered_at`, `updated_at`.
  - Factories: `register_auto(id, name, rule_id, template_id, settings, now)`, `include_manual(id, name, template_id, settings, now)`, `exclude_manual(id, name, now)` (settings None).
  - Commands (each sets `updated_at=now`): `pause(now)`, `resume(now)`, `exclude(now)`, `mark_dropped(now)`, `rename(name, now)`, `reset_to_auto(now)`, `apply_auto_decision(rule_id, template_id, settings, now)` (AUTO tables only, used after `reset_to_auto`: an INCLUDE rule → ACTIVE, and the template settings are copied in if the table has none; `rule_id=None` or an EXCLUDE rule → `EXCLUDED`, existing settings kept), `update_settings(settings, now)`, `record_operation_result(op, succeeded: bool, at)`.
  - Queries: `needs_reconcile_workflow -> bool` (status in ACTIVE, PAUSED); `operation_state(op) -> OperationState` (default `OperationState()`).

- [ ] **Step 1: Write failing tests:**
  - `test_dropped_is_terminal`: after `mark_dropped`, every other command raises `InvalidTableTransition` (except `mark_dropped` itself, which is a no-op).
  - `test_pause_resume_only_from_active_paused`: `pause` on `EXCLUDED` raises; `resume` on `ACTIVE` is a no-op.
  - `test_exclude_manual_has_no_settings_and_no_workflow`: `needs_reconcile_workflow is False`, `settings is None`, `selection == MANUAL`.
  - `test_exclude_sets_manual`: excluding an AUTO table sets `selection=MANUAL`, `status=EXCLUDED`.
  - `test_reset_to_auto_then_apply_include_decision`: MANUAL EXCLUDED table without settings → `reset_to_auto` → `apply_auto_decision(rule, template, settings)` → `ACTIVE`, settings set, `AUTO`.
  - `test_apply_auto_decision_without_rule_excludes_auto_table`: an AUTO table with `apply_auto_decision(None, None, None, now)` becomes `EXCLUDED` (keeps settings) — the only path where an auto table stops being maintained by rules, used only after an explicit reset.
  - `test_apply_auto_decision_ignored_for_manual`: MANUAL table unchanged.
  - `test_update_settings_requires_settings_capable_status`: on `EXCLUDED` without settings raises.
  - `test_backoff_doubles_and_caps`: base 1h; failures 0→1h, 1→2h, 3→8h, 10→24h; success resets to 0.
  - `test_rename_keeps_identity`: same `id`, new `name`, equal by identity.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add managed table aggregate`.

### Task 4: Domain — table observation and maintenance planning

**Files:**
- Create `application/domain/model/observation/`: `table_observation.py`, `partition_spec_info.py`, `partition_field_info.py`, `partition_stats.py`, `manifest_stats.py`, `snapshot_info.py`
- Create `application/domain/model/maintenance/`: `maintenance_plan.py`, `planned_operation.py`
- Create `application/domain/service/`: `compute_reducible_files.py`, `resolve_target_file_size.py`, `plan_scheduled_maintenance.py`, `plan_manual_maintenance.py`
- Test: `tests/application/domain/service/test_*.py`

**Interfaces:**
- Produces:
  - `PartitionFieldInfo(field_id: int, name: str, source_column: str, source_type: str, transform: str)` — `transform` uses Iceberg's string form: `identity`, `year`, `month`, `day`, `hour`, `bucket[N]`, `truncate[W]`, `void`; `source_type` uses Iceberg primitive names (`int`, `long`, `string`, `date`, `timestamp`, `timestamptz`, `boolean`, `decimal(p,s)`, …).
  - `PartitionSpecInfo(spec_id: int, fields: tuple[PartitionFieldInfo, ...])`; `is_unpartitioned -> bool` (no fields or all `void`).
  - `PartitionStats(spec_id: int, values: tuple[str | int | float | bool | None, ...], data_file_count: int, position_delete_file_count: int, equality_delete_file_count: int, total_data_file_size_bytes: int)` — `values` in Iceberg's **internal** representation, aligned with the spec's fields (dates/day = int days since epoch, timestamps = int micros, hour/month/year = int since epoch, decimals = str).
  - `ManifestStats(length_bytes: int)`; `SnapshotInfo(snapshot_id: int, committed_at: datetime)`.
  - `TableObservation(table_uuid: str, properties: dict[str, str], current_snapshot_id: int | None, specs: tuple[PartitionSpecInfo, ...], partitions: tuple[PartitionStats, ...], manifests: tuple[ManifestStats, ...], snapshots: tuple[SnapshotInfo, ...])`.
  - `PlannedOperation(operation: MaintenanceOperation, partitions: tuple[PartitionStats, ...] = ())` — empty `partitions` means whole table; `MaintenancePlan(operations: tuple[PlannedOperation, ...])` always in `MaintenanceOperation.ordered()` order; `is_empty -> bool`.
  - `compute_reducible_files(stats: PartitionStats, target_file_size_bytes: int) -> int`:
    ```
    total = data + position_deletes + equality_deletes
    expected = ceil(total_bytes / target)   # 0 when total_bytes == 0
    return max(0, total - expected)
    ```
  - `resolve_target_file_size(settings: RewriteDataFilesSettings, properties: dict[str, str]) -> int` (settings → `write.target-file-size-bytes` → `536870912`).
  - `plan_scheduled_maintenance(table: ManagedTable, observation: TableObservation, now: datetime) -> MaintenancePlan`.
  - `plan_manual_maintenance(operations: Sequence[MaintenanceOperation]) -> MaintenancePlan` (every named operation, whole table, de-duplicated, canonical order).

- [ ] **Step 1: Write failing tests** (`now = 2026-10-24T12:00Z`, default settings unless stated):
  - `test_reducible_files_formula`: 20 data + 4 pos-delete files, 1 GiB, target 512 MiB → `22`; 1 file of 2 GiB → `0` (clamped); 3 delete-only files, 0 bytes → `3`.
  - `test_target_file_size_resolution_order`.
  - `test_partition_scope_selects_only_partitions_over_threshold`: partitions with reducible 2, 5, 9 and threshold 5 → plan has `REWRITE_DATA_FILES` with exactly the 5 and 9 partitions.
  - `test_table_scope_sums_partitions`: scope TABLE, three partitions each reducible 2 (sum ≥ 5) → whole-table operation (empty `partitions`).
  - `test_unpartitioned_table_plans_whole_table` (Review Focus 1): spec with no fields, one stats row, reducible 10 → whole-table operation even with scope PARTITION.
  - `test_cooldown_skips_operation`: `last_attempt_at = now - 30min`, `min_interval=1h` → no compaction; with `consecutive_failures=2` and last attempt 3 h ago → still skipped (cooldown 4 h).
  - `test_disabled_operation_never_planned`.
  - `test_expire_snapshots_due_only_when_something_expires`: 12 snapshots, 11 older than 1 day, `retain_last=10` → due; 10 snapshots all old → not due; current snapshot never counts as expirable.
  - `test_rewrite_manifests_due_on_small_manifest_count`: 5 manifests < 8 MiB → due; 4 → not due.
  - `test_remove_orphan_files_due_after_interval`: never run → due; last attempt 6 days ago → not due.
  - `test_plan_order_is_canonical` and `test_paused_or_settingless_table_yields_empty_plan` (PAUSED / EXCLUDED → empty).
  - `test_manual_plan_runs_named_operations_whole_table`: `[EXPIRE_SNAPSHOTS, REWRITE_DATA_FILES, EXPIRE_SNAPSHOTS]` → two operations, compaction first, empty partitions.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add table observation and maintenance planner`.

### Task 5: Domain — partition predicate builder

**Files:**
- Create `application/domain/service/build_partition_filters.py`, `application/domain/model/maintenance/spec_filter.py`
- Test: `tests/application/domain/service/test_build_partition_filters.py`

**Interfaces:**
- Consumes: `PartitionSpecInfo`, `PartitionStats` (Task 4).
- Produces: `SpecFilter(spec_id: int, where: str)`; `build_partition_filters(catalog: str, specs: Sequence[PartitionSpecInfo], partitions: Sequence[PartitionStats]) -> tuple[SpecFilter, ...]` sorted by `spec_id`; empty `partitions` → `()` (caller runs whole table).

Rules (from the spec, verified against Iceberg 1.10.0 source):
- Columns quoted with backticks; strings single-quoted with `'` doubled; booleans `true`/`false`; decimals and numbers unquoted.
- Field term by transform: `identity` → `` `col` = <literal rendered by source_type> `` (date → `DATE 'yyyy-mm-dd'`, timestamp/timestamptz micros → `TIMESTAMP 'yyyy-mm-dd HH:MM:SS.ffffff'` in UTC); `year|month|hour` → `{catalog}.system.{years|months|hours}(`col`) = <int>`; `day` → `{catalog}.system.days(`col`) = DATE '<epoch + n days>'`; `bucket[N]` → `{catalog}.system.bucket(N, `col`) = <int>`; `truncate[W]` → `{catalog}.system.truncate(W, `col`) = <literal of source type>`; `void` → no term.
- Null value (any transform) → `` `col` IS NULL ``.
- Time transforms additionally add a source-column range: `` `col` >= <start> AND `col` < <end> `` (DATE literals for `date` columns, TIMESTAMP literals for timestamp columns; start/end = the period's bounds in UTC).
- One partition = terms joined by ` AND ` and wrapped in parentheses; partitions in the same spec joined by ` OR `.
- A partition whose terms are all empty (all `void`/unpartitioned) makes that spec's filter `""`, which the caller treats as "whole table for this spec".

- [ ] **Step 1: Write failing tests** with exact expected strings, catalog `"iceberg"`:
  - `test_identity_string_escapes_quotes`: value `"o'neil"` → `` (`region` = 'o''neil') ``.
  - `test_day_transform_uses_date_literal_and_range`: day value `20385` on `timestamptz` column `ts` → `(iceberg.system.days(`ts`) = DATE '2025-10-24' AND `ts` >= TIMESTAMP '2025-10-24 00:00:00.000000' AND `ts` < TIMESTAMP '2025-10-25 00:00:00.000000')`.
  - `test_hour_month_year_use_ints`: hour `490000`, month `669`, year `55` render `= 490000`, `= 669`, `= 55` with correct ranges (month 669 → 2025-10-01..2025-11-01).
  - `test_bucket_and_truncate`: `bucket[16]` value 3 on `id` → `iceberg.system.bucket(16, `id`) = 3`; `truncate[4]` value `"abcd"` → `iceberg.system.truncate(4, `name`) = 'abcd'`.
  - `test_null_partition_value_uses_is_null`.
  - `test_multi_field_partition_and_multiple_partitions`: two partitions with (day, bucket) → `(... AND ...) OR (... AND ...)`.
  - `test_void_fields_are_skipped` (Review Focus 1).
  - `test_one_filter_per_spec_id` (Review Focus 1): partitions from specs 0 and 1 → two `SpecFilter`s, spec 0 first, each only containing its own spec's fields.
  - `test_identity_date_and_timestamp_literals`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): build partition filters for rewrite_data_files`.

### Task 6: Domain — maintenance run aggregate

**Files:**
- Create `application/domain/model/maintenance_run/`: `maintenance_run.py`, `maintenance_run_id.py`, `operation_run.py`, `run_status.py`, `operation_run_status.py`, `trigger_type.py`, `invalid_run_transition.py`
- Create `application/domain/service/spark_application_name.py`
- Test: `tests/application/domain/model/maintenance_run/`, `tests/application/domain/service/test_spark_application_name.py`

**Interfaces:**
- Produces:
  - `TriggerType` = `SCHEDULED`, `EVENT`, `MANUAL`; `RunStatus` = `PENDING`, `RUNNING`, `SUCCEEDED`, `PARTIALLY_FAILED`, `FAILED`; `OperationRunStatus` = `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `SKIPPED`.
  - `OperationRun` (VO, replaced on change): `operation`, `status`, `attempts: int`, `started_at`, `finished_at`, `spark_application: str | None`, `metrics: dict[str, int]`, `error: str | None`, `expected_files: int | None`.
  - `MaintenanceRun(AggregateRoot[MaintenanceRunId])`: `table_uuid: TableUuid`, `trigger: TriggerType`, `operations: tuple[OperationRun, ...]` (canonical order), `created_at`, `finished_at`; `create(id, table_uuid, trigger, operations, now)`; `start_attempt(op, attempt: int, spark_application: str, now)`; `succeed(op, attempt, metrics, now)`; `fail(op, attempt, error, now)`; `skip(op, reason, now)`; `status -> RunStatus` (derived).
  - `spark_application_name(run_id: str, operation: MaintenanceOperation, attempt: int) -> str` = `f"tm-{code}-{run_id.replace('-', '')[:20]}-a{attempt}"`, `code` ∈ `rdf`, `rm`, `es`, `rof`; always ≤ 63 chars, lowercase.

- [ ] **Step 1: Write failing tests:**
  - `test_status_rollup`: none started → PENDING; any RUNNING/PENDING after start → RUNNING; all SUCCEEDED (SKIPPED ignored) → SUCCEEDED; mixed → PARTIALLY_FAILED; all FAILED → FAILED; all SKIPPED → SUCCEEDED; `finished_at` set when the last operation becomes terminal.
  - `test_stale_attempt_result_ignored`: `start_attempt(op, 2, ...)`; `succeed(op, attempt=1, ...)` leaves status RUNNING and attempts 2.
  - `test_duplicate_result_is_idempotent`: a second `succeed` for the same attempt changes nothing; `fail` after `succeed` for the same attempt raises `InvalidRunTransition`.
  - `test_unknown_operation_raises`.
  - `test_spark_application_name_is_dns_safe_and_deterministic`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add maintenance run aggregate`.

### Task 7: Repository ports and SQL repositories

**Files:**
- Create ports `application/port/outbound/{managed_table,discovery_rule,policy_template,discovery,maintenance_run}/` with `managed_tables_repo.py`, `discovery_rules_repo.py`, `policy_templates_repo.py`, `discovery_settings_repo.py`, `maintenance_runs_repo.py` + `__init__.py`
- Create adapters `adapter/outbound/sql/`: keep `engine_factory.py`, `metadata.py`; add one `*_table.py` + one `*_sql_repo.py` (+ row mappers) per aggregate under `adapter/outbound/{managed_table,discovery_rule,policy_template,discovery,maintenance_run}/sql/`
- Test: `tests/adapter/outbound/*/test_*_sql_repo.py` (SQLite in-memory)

**Interfaces:**
- Produces (all extend `Repository[...]`; `create`, `get(id) -> E | None`, `list_all() -> list[E]` from the base plus):
  - `ManagedTablesRepo`: `update(table) -> ManagedTable`, `find_by_name(name: TableName) -> ManagedTable | None`, `list_by_statuses(statuses: Sequence[TableStatus]) -> list[ManagedTable]`.
  - `DiscoveryRulesRepo`: `update`, `delete(id) -> None`, `count_by_template(template_id) -> int`.
  - `PolicyTemplatesRepo`: `update`, `delete(id)`, `find_by_name(name) -> PolicyTemplate | None`.
  - `DiscoverySettingsRepo`: `get_settings() -> DiscoverySettings` (default enabled when absent), `save(settings) -> None`.
  - `MaintenanceRunsRepo`: `update(run)`, `list_by_table(table_uuid, limit: int = 50) -> list[MaintenanceRun]` (newest first).
  - Settings and operation states are stored as JSON columns; a `settings_json` codec lives in `adapter/outbound/sql/maintenance_settings_codec.py` (durations as ISO-8601 seconds ints).
  - `create_schema(engine) -> None` in `adapter/outbound/sql/create_schema.py` (calls `metadata.create_all`). Seeding the `default` template is not a repo concern: the migrate component (Task 17) calls the `create_policy_template` use case (Task 8).

- [ ] **Step 1: Write failing round-trip tests** per repo: create → get equals field-by-field (settings, operation states, enums, timezone-aware datetimes survive); `update` persists changes; `find_by_name` exact match; `list_by_statuses`; `MaintenanceRunsRepo.list_by_table` ordering and limit; `DiscoverySettingsRepo.get_settings()` on empty DB returns enabled.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement ports and SQL adapters. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add repositories for control plane aggregates`.

### Task 8: Use cases — rules, templates, discovery switch, table management

**Files:**
- Create outbound gateway ports (no adapters yet): `application/port/outbound/workflow/send_table_signal/` (`SendTableSignalGateway`, input), `application/port/outbound/discovery/update_discovery_schedule/` (`UpdateDiscoveryScheduleGateway`, input), `application/port/outbound/catalog/read_catalog/` (`ReadCatalogGateway`, input/output — method list below; adapter in Task 10)
- Create inbound ports + services for each use case in the table below
- Create `application/exceptions/` (`NotFoundError`, `ConflictError`, `ValidationError` — application-level; services translate domain exceptions into these)
- Test: `tests/application/service/<group>/test_<verb_noun>.py` using in-memory fakes in `tests/fakes/` (fake repos, fake gateways recording calls)

**Interfaces:**
- `SendTableSignalGateway.send(input: SendTableSignalGatewayInput) -> None` with `table_uuid: str`, `signal: str`, `payload: dict`, `start_if_missing: bool`.
- `UpdateDiscoveryScheduleGateway.update(input: UpdateDiscoveryScheduleGatewayInput) -> None` with `paused: bool`.
- `ReadCatalogGateway`: `list_tables(input: ReadCatalogGatewayListInput) -> list[ReadCatalogGatewayTableRef]` (`catalog`, `namespace: str | None`; ref = `catalog, namespace, table`); `load_table(ref) -> ReadCatalogGatewayTableRef + table_uuid` as `ReadCatalogGatewayTable | None`; `observe_table(ref) -> ReadCatalogGatewayObservation | None` (primitive mirror of `TableObservation`; times as ISO strings). One object per file: the output classes go in `table_ref.py`, `table.py`, `observation.py` inside the gateway dir (no single `output.py`); extend `test_outbound_port_structure.py`'s allowed file names and primitive-only check to cover them.

| Group / use case | Input | Output | Behaviour |
|---|---|---|---|
| `policy_template/create_policy_template` | name, settings (primitive dict) | template dict | name unique → `ConflictError` |
| `policy_template/update_policy_template` | id, name?, settings? | template dict | |
| `policy_template/delete_policy_template` | id | — | referenced by a rule → `ConflictError` |
| `policy_template/list_policy_templates`, `get_policy_template` | —/id | list/one | |
| `discovery_rule/create_discovery_rule`, `update_…`, `delete_…`, `list_discovery_rules` | priority, effect, catalog/namespace/table patterns, template_id?, enabled | rule dict | template must exist |
| `discovery/get_discovery_settings`, `update_discovery_settings` | enabled | enabled | update calls `UpdateDiscoveryScheduleGateway(paused=not enabled)` after saving |
| `managed_table/list_managed_tables` | status filter? | list | |
| `managed_table/get_managed_table` | uuid | table incl. settings, operation states | |
| `managed_table/update_managed_table_settings` | uuid, settings | table | then signal `settings_changed` |
| `managed_table/pause_managed_table`, `resume_managed_table` | uuid | table | signal `pause` / `resume` |
| `managed_table/include_managed_table` | catalog, namespace, table, template_id | table | load uuid via `ReadCatalogGateway.load_table`; not found → `NotFoundError`; existing row → MANUAL ACTIVE with template settings (re-activates EXCLUDED); new row → `include_manual`; then `send(signal="resume", start_if_missing=True)` so the workflow starts |
| `managed_table/exclude_managed_table` | catalog, namespace, table | table | existing row → `exclude`; else `exclude_manual` (needs uuid from catalog); signal `stop` |
| `managed_table/reset_managed_table_selection` | uuid | table | `reset_to_auto`, re-run `match_discovery_rule` + template copy, `apply_auto_decision`; start or stop the workflow to match `needs_reconcile_workflow` |
| `managed_table/trigger_maintenance` | uuid, operations | accepted bool | table must need a workflow; signal `trigger_now` with `{"operations": [...]}`, `start_if_missing=True` |

- [ ] **Step 1: Write failing service tests** for every row, including: `test_delete_template_in_use_conflicts`; `test_disabling_discovery_pauses_schedule`; `test_include_unknown_table_not_found`; `test_include_reactivates_excluded_table_as_manual`; `test_exclude_unregistered_table_creates_row_without_settings`; `test_reset_selection_applies_matching_include_rule`; `test_trigger_on_dropped_table_conflicts`; `test_settings_update_signals_workflow`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement ports, inbound ports, services, fakes. **Step 4:** Run all checks → PASS (architecture tests cover structure).
- [ ] **Step 5: Commit** `feat(table-maintenance): add management use cases`.

### Task 9: Use cases — discovery sync, table hints, reconcile lifecycle

**Files:**
- Create gateway ports: `application/port/outbound/spark/submit_maintenance_job/`, `spark/read_maintenance_job/`, `spark/delete_maintenance_job/`, `workflow/send_maintenance_result/`, `workflow/send_discovery_request/`
- Create inbound ports + services in the table below
- Test: `tests/application/service/{discovery,reconcile,maintenance_run}/`

**Interfaces:**
- `SubmitMaintenanceJobGateway.submit(input) -> None` — input: `app_name, run_id, operation, attempt, catalog, namespace, table, where: list[str], procedure_args: dict, callback_url`; idempotent (same `app_name` twice = one job).
- `ReadMaintenanceJobGateway.read(input: app_name) -> ReadMaintenanceJobGatewayOutput(state: str, error: str | None)`; `state` ∈ `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `NOT_FOUND`.
- `DeleteMaintenanceJobGateway.delete(input: app_name) -> None`.
- `SendMaintenanceResultGateway.send(input: run_id, operation, attempt, succeeded, metrics: dict, error) -> None`.
- `SendDiscoveryRequestGateway.send(input: catalog, namespace: str | None) -> None`.

| Group / use case | Input | Output | Behaviour |
|---|---|---|---|
| `discovery/sync_discovered_tables` | catalog, namespace? | registered, renamed, dropped counts | list tables; for each: load uuid; unknown uuid + discovery enabled → match rules → INCLUDE: `register_auto` with template copy + signal `resume` start-if-missing; EXCLUDE/no match: nothing; known uuid with new name → `rename`; then registry ACTIVE/PAUSED tables in scope whose uuid was not seen → `mark_dropped` + signal `stop`. Scope = whole catalog when namespace is None, else that namespace only. MANUAL tables are renamed/dropped but never re-decided |
| `discovery/process_table_hint` | catalog, namespace, table?, event_type | action taken | `table` None → `SendDiscoveryRequestGateway(catalog, namespace)`; else `load_table`: found + registered under same uuid → if `needs_reconcile_workflow` signal `table_updated`; found + new name → rename; found + unregistered → run the single-table version of sync; not found → if a row has that name, request a namespace discovery (confirms drop by uuid scan) |
| `reconcile/plan_table_maintenance` | table_uuid, now, manual_operations? | `{status: "planned"|"skip", reason, reconcile_interval_seconds, operations: [{operation, filters: [{spec_id, where}], procedure_args}]}` | load table; not found/not needing workflow → skip with reason `dropped`/`excluded`; manual → `plan_manual_maintenance`; else observe via `ReadCatalogGateway.observe_table` (None → skip `not_found`) and `plan_scheduled_maintenance`; compaction filters via `build_partition_filters(table.name.catalog, …)`; `procedure_args` per operation from settings (`older_than` as ISO timestamp `now - older_than`, `retain_last`, `target_file_size_bytes`, `min-input-files`=2, `partial-progress.enabled`=true) |
| `maintenance_run/create_maintenance_run` | run_id, table_uuid, trigger, operations | run | idempotent: existing id returns it |
| `reconcile/submit_maintenance_operation` | run_id, operation, attempt, plan entry, callback_base_url | app_name | `start_attempt` then gateway submit with `spark_application_name(...)`; callback URL `{base}/v1/runs/{run_id}/operations/{operation}/result` |
| `reconcile/get_maintenance_job_status` | app_name | state, error | |
| `maintenance_run/record_maintenance_operation_result` | run_id, operation, attempt, succeeded, metrics, error, now | run status | `succeed`/`fail`; then on the table `record_operation_result` (separate save; documented as two aggregates updated in sequence, run first) |
| `maintenance_run/process_maintenance_callback` | run_id, operation, attempt, succeeded, metrics, error | accepted | run must exist → else `NotFoundError`; forwards via `SendMaintenanceResultGateway` (the workflow decides staleness) |
| `maintenance_run/list_maintenance_runs`, `get_maintenance_run` | table_uuid / run_id | runs / run | |

- [ ] **Step 1: Write failing tests**, including: `test_sync_registers_include_match_with_template_copy`; `test_sync_skips_when_discovery_disabled`; `test_sync_marks_missing_tables_dropped_only_in_scope`; `test_sync_rename_keeps_settings`; `test_sync_never_redecides_manual_tables`; `test_table_hint_without_name_requests_namespace_discovery`; `test_table_hint_for_registered_table_signals_but_cooldown_blocks_replan` (Review Focus 5: hint signals `table_updated`, and a following `plan_table_maintenance` within the cooldown returns no operations); `test_plan_skip_reasons`; `test_plan_compaction_has_one_filter_per_spec`; `test_manual_plan_ignores_disabled_and_cooldown`; `test_submit_is_idempotent_by_app_name`; `test_record_result_updates_run_and_table_backoff`; `test_callback_unknown_run_not_found`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add discovery and reconcile use cases`.

### Task 10: Outbound — PyIceberg catalog gateway

**Files:**
- Create `adapter/outbound/catalog/read_catalog_pyiceberg_gateway.py` (+ helpers `observation_mapper.py`)
- Test: `tests/adapter/outbound/catalog/test_read_catalog_pyiceberg_gateway.py` using a PyIceberg `SqlCatalog` (SQLite + local warehouse in `tmp_path`) with real PyArrow writes

**Interfaces:**
- Consumes: `ReadCatalogGateway` port (Task 8). Constructor `ReadCatalogPyIcebergGateway(catalog_factory: Callable[[str], pyiceberg.catalog.Catalog])` — one PyIceberg catalog per Polaris catalog name; the bootstrap passes a factory using `load_catalog(name, type="rest", uri=..., credential=..., warehouse=name, scope=..., **s3 props)`.
- Partition stats come from the current snapshot's manifests (data and delete entries), grouped by `(spec_id, partition record)`, values in Iceberg internal representation (convert any `date`/`datetime` PyIceberg returns back to int days/micros).

- [ ] **Step 1: Write failing tests:** table partitioned by `day(ts)` + `bucket(4, id)` with 3 appends → `observe_table` returns one `PartitionStats` per (day, bucket) with correct file counts and int day values; unpartitioned table → one stats row with `values == []`; after a spec evolution (add `identity(region)`), stats rows carry both spec ids; `load_table` returns the metadata `table-uuid`; missing table → None; `list_tables` with and without namespace (multi-level namespace joined with `.`); snapshots and manifest lengths present.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): read iceberg metadata through pyiceberg`.

### Task 11: Spark runtime and Kubernetes Spark gateways

**Files:**
- Modify `src/table-maintenance/runtime/spark/` (`main.py`, `sql_builder.py`, `configs/`, `Dockerfile`, `README.md`, tests in `runtime/spark/tests/`)
- Create `adapter/outbound/spark/{submit_maintenance_job_k8s_gateway.py,read_maintenance_job_k8s_gateway.py,delete_maintenance_job_k8s_gateway.py,spark_application_manifest.py,spark_k8s_config.py}`
- Test: `tests/adapter/outbound/spark/` (mock `CustomObjectsApi`)

**Interfaces:**
- Runtime contract: env `GLAC_REQUEST` = JSON of the submit gateway input (Task 9). The runtime runs one `CALL {catalog}.system.{operation}(...)` per filter (`where => '<filter>'`, SQL single quotes doubled; no filter or `""` → whole table), sums integer result columns across calls, then POSTs `{"attempt": n, "succeeded": bool, "metrics": {...}, "error": str|null}` to `callback_url` (stdlib `urllib`, 3 tries, 5 s apart). Exit code 0 on success, 1 on failure (after posting). Session conf must include `spark.sql.session.timeZone=UTC`.
- `SparkK8sConfig(namespace="lakehouse-maintenance-operations", image, image_pull_policy="Never", service_account, spark_version="4.0.0", iceberg_version="1.10.1", catalog_uri, catalog_credential_secret, s3_endpoint, s3_secret_name, driver/executor resources)`.
- `build_spark_application(config, input) -> dict` producing a `SparkApplication` (`sparkoperator.k8s.io/v1beta2`) named `input.app_name`, labels `app.kubernetes.io/part-of=table-maintenance`, `table-maintenance/run-id`, Iceberg runtime + aws-bundle jars, `spark.sql.catalog.{catalog}` REST conf (warehouse = catalog name), S3 creds from the secret via `envFrom`, `restartPolicy: Never`.
- Submit: create; HTTP 409 → treat as already submitted. Read: map `.status.applicationState.state` (`COMPLETED`→COMPLETED, `FAILED`/`SUBMISSION_FAILED`/`FAILING`→FAILED, others → RUNNING/PENDING; 404 → NOT_FOUND). Delete: ignore 404.

- [ ] **Step 1: Write failing runtime tests:** `test_call_per_filter_with_escaped_where`; `test_whole_table_when_no_filters`; `test_metrics_summed_across_calls`; `test_failure_posts_error_and_exits_1` (Spark mocked).
- [ ] **Step 2: Write failing gateway tests:** manifest snapshot (name, namespace, image, jars, catalog conf keys, UTC timezone, `GLAC_REQUEST` JSON); `test_submit_conflict_is_success`; `test_read_maps_states`; `test_delete_ignores_not_found`.
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement. **Step 5:** Run backend checks and `uv run --project src/table-maintenance/runtime/spark --directory src/table-maintenance/runtime/spark pytest -q` → PASS.
- [ ] **Step 6: Commit** `feat(table-maintenance): run planned maintenance on spark with result callback`.

### Task 12: Outbound — Temporal client gateways

**Files:**
- Create `adapter/outbound/workflow/{send_table_signal_temporal_gateway.py,send_maintenance_result_temporal_gateway.py,send_discovery_request_temporal_gateway.py}`, `adapter/outbound/discovery/update_discovery_schedule_temporal_gateway.py`
- Test: `tests/adapter/outbound/workflow/` against `temporalio.testing.WorkflowEnvironment.start_local()` (or time-skipping) with tiny stub workflows registered under the real workflow names

**Interfaces:**
- Constructors take a connected `temporalio.client.Client` and run async calls through a sync bridge (`asyncio.run_coroutine_threadsafe` on a loop owned by the component) — the gateway ports are synchronous.
- Send table signal: `start_if_missing=True` → `client.start_workflow("TableReconcileWorkflow", TableReconcileWorkflowInput(table_uuid), id=table_reconcile_workflow_id(uuid), task_queue=TASK_QUEUE, start_signal=signal, start_signal_args=[payload], id_conflict_policy=USE_EXISTING)`; else `get_workflow_handle(...).signal(...)`, swallowing "workflow not found".
- Maintenance result: signal `maintenance-{run_id}` with `operation_result`.
- Discovery request: start `DiscoveryWorkflow` with id `table-discovery-adhoc-{catalog}-{namespace or "all"}` and `id_conflict_policy=USE_EXISTING`.
- Schedule update: `get_schedule_handle(DISCOVERY_SCHEDULE_ID).pause()/unpause()`.
- Workflow input dataclasses (`TableReconcileWorkflowInput`, `DiscoveryWorkflowInput`, `MaintenanceWorkflowInput`, `CapacityLimiterInput`) live in `adapter/temporal_contracts/`, a neutral package that both `adapter.inbound.temporal` and `adapter.outbound.workflow` import (outbound must not import inbound). In `.importlinter`, allow both to import it, and forbid it from importing anything project-internal except `application.domain.model.maintenance`.

- [ ] **Step 1: Write failing tests:** signal-with-start creates exactly one workflow for two calls; plain signal to a missing workflow does not raise; maintenance result reaches the stub; schedule pause/unpause toggles `describe().schedule.state.paused`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add temporal client gateways`.

### Task 13: Temporal — activities, capacity limiter, maintenance workflow

**Files:**
- Create `adapter/inbound/temporal/activities/{reconcile_activities.py,maintenance_activities.py,discovery_activities.py}`, `adapter/inbound/temporal/workflows/{capacity_limiter_workflow.py,maintenance_workflow.py}`
- Test: `tests/adapter/inbound/temporal/` with `WorkflowEnvironment.start_time_skipping()` and mocked activities

**Interfaces:**
- Activities are classes taking use cases in `__init__`, methods decorated `@activity.defn(name=...)`: `plan_table_maintenance`, `create_maintenance_run`, `submit_maintenance_operation`, `get_maintenance_job_status`, `record_maintenance_operation_result`, `delete_maintenance_job`, `sync_discovered_tables`, `signal_capacity_acquire` (signal-with-start of the limiter via the client), `signal_parent` (signals the reconcile workflow by id). Each wraps exactly one use case or gateway call.
- `CapacityLimiterWorkflow.run(CapacityLimiterInput(limit: int, lease_seconds: int = 21600, holders: dict, queue: list))`: signals `acquire(request_id, requester_workflow_id)` and `release(request_id)`; grants FIFO by signalling `capacity_granted(request_id)` to the requester; a holder older than `lease_seconds` is evicted; duplicate acquire for a held/queued `request_id` is a no-op; Continue-As-New when suggested, carrying holders and queue.
- `MaintenanceWorkflow.run(MaintenanceWorkflowInput(run_id, table_uuid, parent_workflow_id, trigger, plan))`: `create_maintenance_run`; for each planned operation in order: for attempt 1..3: acquire capacity (request_id `{run_id}-{op}-{attempt}`), `submit_maintenance_operation`, wait for `operation_result` with matching attempt **or** poll `get_maintenance_job_status` every 30 s (FAILED/NOT_FOUND → failure "spark job failed"/"spark job missing"; COMPLETED with no callback for 120 s → success with empty metrics and note), release capacity (in `finally`), `record_maintenance_operation_result`; success → next operation; failure → sleep backoff (60 s, then 120 s) and retry; after attempt 3 the operation stays FAILED and the workflow continues with the next operation. Finally `delete_maintenance_job` for its apps and `signal_parent(maintenance_finished, run_id)`.

- [ ] **Step 1: Write failing tests:**
  - `test_operations_run_in_order_and_parent_signalled`.
  - `test_failed_operation_retried_three_attempts_total_then_next_operation_runs`.
  - `test_stale_attempt_callback_is_ignored` (Review Focus 3): attempt-1 result arriving during attempt 2 does not complete attempt 2.
  - `test_polling_detects_crashed_driver`: no callback, status FAILED → recorded failure.
  - `test_capacity_never_exceeds_limit`: limit 2, three workflows acquire → third granted only after a release.
  - `test_capacity_lease_expires_when_holder_never_releases` (Review Focus 2): holder never releases, after `lease_seconds` the queued requester is granted.
  - `test_capacity_released_when_submit_activity_fails`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (deterministic workflow code only; time via `workflow.now()`, sleeps via `workflow.sleep`). **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add maintenance and capacity workflows`.

### Task 14: Temporal — table reconcile and discovery workflows

**Files:**
- Create `adapter/inbound/temporal/workflows/{table_reconcile_workflow.py,discovery_workflow.py}`, `adapter/inbound/temporal/ensure_discovery_schedule.py`
- Test: `tests/adapter/inbound/temporal/test_table_reconcile_workflow.py`, `test_discovery_workflow.py`

**Interfaces:**
- `TableReconcileWorkflow.run(TableReconcileWorkflowInput(table_uuid, in_flight_run_id=None, pending_manual=None))`; signals `settings_changed`, `table_updated`, `trigger_now({"operations": [...]})`, `pause`, `resume`, `stop`, `maintenance_finished(run_id)`. Loop: wait until timer (`reconcile_interval_seconds` from the last plan; 3600 on first loop) or any signal; if a run is in flight, remember a pending manual trigger and wait; else `plan_table_maintenance` (manual operations if a manual trigger is pending, consumed when started); `status == "skip"` with reason `dropped`/`excluded` → end; planned non-empty → start child `MaintenanceWorkflow` id `maintenance_workflow_id(workflow.uuid4())`, `parent_close_policy=ABANDON`, record in flight. `stop` → end after the in-flight run's `maintenance_finished` (or immediately when none). Continue-As-New when `workflow.info().is_continue_as_new_suggested()` or every 200 iterations, carrying `in_flight_run_id` and `pending_manual`.
- `DiscoveryWorkflow.run(DiscoveryWorkflowInput(catalog, namespace=None))` → `sync_discovered_tables`.
- `ensure_discovery_schedule(client, catalogs: list[str], interval=10 min, paused: bool) -> None`: create schedule `table-discovery` (one action per catalog: start `DiscoveryWorkflow`) if missing, else update interval/paused; overlap policy SKIP.

- [ ] **Step 1: Write failing tests:**
  - `test_timer_triggers_plan_every_interval`.
  - `test_trigger_now_while_in_flight_runs_after_finish`.
  - `test_child_result_received_after_continue_as_new` (child signals by workflow id).
  - `test_dropped_signal_ends_workflow_after_in_flight_run` (Review Focus 4).
  - `test_skip_excluded_ends_workflow`.
  - `test_pause_skips_plans_resume_restores`.
  - `test_discovery_schedule_created_once_and_paused_flag_applied`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add table reconcile and discovery workflows`.

### Task 15: Inbound — web API

**Files:**
- Create `adapter/inbound/web/{discovery_rule,policy_template,discovery,managed_table,maintenance_run}/` with `router.py` + `dto.py` per group, `adapter/inbound/web/error_handlers.py`
- Create `bootstrap/dependencies/*` providers for each use case
- Test: `tests/adapter/inbound/web/` with `TestClient` and fake use cases

**Interfaces (all under `/v1`, JSON):**
- `GET/POST /discovery-rules`, `PATCH/DELETE /discovery-rules/{rule_id}`
- `GET/PUT /discovery` (`{"enabled": bool}`), `POST /discovery/scan` (`{"catalog", "namespace"?}` → 202)
- `GET/POST /policy-templates`, `GET/PATCH/DELETE /policy-templates/{template_id}`
- `GET /tables?status=`, `GET /tables/{table_uuid}`, `PUT /tables/{table_uuid}/settings`, `POST /tables/{table_uuid}/pause|resume|reset-selection`, `POST /tables/include`, `POST /tables/exclude`, `POST /tables/{table_uuid}/maintenance` (`{"operations": [...]}` → 202), `GET /tables/{table_uuid}/runs`
- `GET /runs/{run_id}`, `POST /runs/{run_id}/operations/{operation}/result` (callback → 202)
- `GET /healthz`
- Errors: `NotFoundError` 404, `ConflictError` 409, `ValidationError` 422; body `{"detail": str}`.
- Settings JSON shape (shared by templates and tables): `{"reconcile_interval_seconds", "rewrite_data_files": {"enabled", "min_interval_seconds", "scope", "target_file_size_bytes", "min_reducible_files"}, "rewrite_manifests": {...}, "expire_snapshots": {"enabled", "min_interval_seconds", "older_than_seconds", "retain_last"}, "remove_orphan_files": {"enabled", "min_interval_seconds", "older_than_seconds"}}`; every field optional on input (defaults from Task 2).

- [ ] **Step 1: Write failing tests:** one happy-path test per route; `test_unknown_operation_name_returns_422`; `test_orphan_older_than_below_one_day_returns_422`; `test_callback_for_unknown_run_returns_404` (Review Focus 3); `test_trigger_dropped_table_returns_409`; DTO naming passes `test_dto_naming.py`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): add control plane api`.

### Task 16: Inbound — Polaris event consumer

**Files:**
- Create `adapter/inbound/event_consumer/{polaris_event.py,map_polaris_event.py,consumer_loop.py}`
- Test: `tests/adapter/inbound/event_consumer/`

**Interfaces:**
- Kafka client: prefer `confluent-kafka`; if it has no Python 3.14 wheel, use `aiokafka`. Group id `table-maintenance-event-consumer`, `auto.offset.reset=latest`, commit offsets after the use case returns (at-least-once; use cases are idempotent).
- `PolarisEvent` (adapter DTO): `event_type`, `catalog_name`, `namespace: list[str]`, `table_name: str | None`, `event_id`.
- `map_polaris_event(raw: bytes) -> ProcessTableHintUseCaseInput | None`: table-changing types (`AFTER_UPDATE_TABLE`, `AFTER_CREATE_TABLE`, `AFTER_DROP_TABLE`, `AFTER_RENAME_TABLE`, `AFTER_REGISTER_TABLE`) → hint with table (for rename use the destination identifier fields present in the payload); `BEFORE_CREATE_TABLE` without `table_name` → namespace hint; everything else → `None`. Verify rename/register field names against live events or Polaris 1.8.0 source before finalising.
- `run_consumer_loop(consumer, use_case, stop_event)`: never crashes on a bad record; logs and continues.

- [ ] **Step 1: Write failing tests:** `test_update_table_maps_to_table_hint`; `test_before_create_without_name_maps_to_namespace_hint`; `test_read_events_ignored`; `test_malformed_event_is_skipped` (Review Focus 5: invalid JSON / missing `catalog_name` → None, loop continues and commits); `test_multi_level_namespace_joined_with_dot` (Review Focus 5); `test_use_case_error_does_not_stop_loop`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks → PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): consume polaris catalog events`.

### Task 17: Bootstrap — settings and composition roots

**Files:**
- Modify/create `bootstrap/configs/{app_settings.py,temporal_settings.py,catalog_settings.py,kafka_settings.py,spark_settings.py,postgres_settings.py,sqlite_settings.py,database_backend.py,component.py}`
- Create `bootstrap/{api.py,worker.py,event_consumer.py,migrate.py}`; modify `entrypoint.py`, `Dockerfile`
- Test: `tests/bootstrap/`

**Interfaces:**
- `AppSettings` (pydantic-settings, prefix `GLAC_`, delimiter `__`): `component`, `database_backend`, `postgres.db_url`, `temporal.address`, `temporal.namespace="default"`, `temporal.task_queue="table-maintenance"`, `catalog.uri`, `catalog.credential`, `catalog.scope="PRINCIPAL_ROLE:ALL"`, `catalog.names=["iceberg"]`, `catalog.s3_endpoint`, `kafka.bootstrap_servers`, `kafka.topic="polaris-catalog-events"`, `spark.*` (Task 11 config), `callback_base_url`, `capacity_limit=2`, `discovery_interval_seconds=600`.
- `migrate.main()`: `create_schema(engine)`; if no templates exist, create template `"default"` with default settings; no discovery rules.
- `worker.main()`: connect Temporal, `ensure_discovery_schedule(paused=not discovery_settings.enabled)`, ensure the capacity limiter is running (signal-with-start no-op), run `Worker(task_queue, workflows=[...], activities=[...])`.
- `api.py`: FastAPI app with routers + error handlers; `event_consumer.main()`: consumer loop.

- [ ] **Step 1: Write failing tests:** settings parse nested env vars; each composition root builds without connecting (inject fakes/factories); `test_migrate_seeds_default_template_once` (twice → one template, zero rules).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run all checks; `docker build` the backend image succeeds.
- [ ] **Step 5: Commit** `feat(table-maintenance): wire control plane components`.

### Task 18: Helm chart and wave 25 deployment

**Files:**
- Create `platform/25-lakehouse-control-plane/chart/` (`Chart.yaml`, `values.yaml`, `templates/`: postgres Deployment (Recreate) + PVC + Service + Secret, `migrate` Job (helm pre-install/pre-upgrade hook, after DB ready via init container `pg_isready`), `api` Deployment + Service (`table-maintenance-api:8000`), `worker` Deployment, `event-consumer` Deployment, ConfigMap/Secret for `GLAC_*`, ServiceAccount + Role/RoleBinding for the worker in `lakehouse-maintenance-operations` (sparkapplications: create/get/list/delete), Spark driver ServiceAccount + Role there)
- Modify `platform/25-lakehouse-control-plane/{bootstrap.sh,validate.sh,README.md}`; create `platform/25-lakehouse-control-plane/build.sh`
- Modify `platform/11-spark-operator/values.yaml` (`jobNamespaces` += `lakehouse-maintenance-operations`)
- Delete `platform/25-table-maintenance`, `platform/25-tbl-maint-bcknd`, `platform/25-tbl-maint-db`, `platform/25-tbl-maint-schdlr`
- Modify `CLAUDE.md` (Project Status: wave 25 deployed components, on-hold list, follow-ups), `tasks/apps.yml` only if the wave's status checks change

**Interfaces:**
- `build.sh`: builds `table-maintenance-backend` and `table-maintenance-spark` images tagged with the short git SHA of the last commit touching their source (plus `-dirty` suffix if uncommitted), `minikube image load -p "${KUBE_CONTEXT}"`, prints the tags.
- `bootstrap.sh`: namespaces (as today); copy RustFS credentials (`rustfs-secret` in `object-storage`) into `lakehouse-control-plane` and `lakehouse-maintenance-operations` as Secret `table-maintenance-s3` with keys `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`; Polaris credential the same way `23-trino` obtains it (dev root credential); run `build.sh`; `helm upgrade --install table-maintenance ./chart --namespace lakehouse-control-plane --set image tags --wait --timeout 600s --kube-context "${KUBE_CONTEXT}"`.
- `validate.sh`: rollouts of postgres/api/worker/event-consumer; `curl` `/v1/healthz` from inside the api pod; Temporal admin-tools `temporal schedule describe --schedule-id table-discovery` succeeds and `temporal workflow describe --workflow-id maintenance-capacity` is Running.

- [ ] **Step 1:** Write the chart; `helm lint` and `helm template` render cleanly (no unpinned images, no comments).
- [ ] **Step 2:** Update `11-spark-operator` values and redeploy that wave (`bash platform/11-spark-operator/bootstrap.sh` + `validate.sh` with `KUBE_CONTEXT=retail-lakehouse`).
- [ ] **Step 3:** Run `bash platform/25-lakehouse-control-plane/bootstrap.sh` then `validate.sh` → both log success.
- [ ] **Step 4:** Remove the four old `25-*` dirs; grep the repo for their names (outside ArgoCD/on-hold paths) and fix references; update `CLAUDE.md` and the wave README.
- [ ] **Step 5:** `task apps:validate KUBE_CONTEXT=retail-lakehouse` exits 0.
- [ ] **Step 6: Commit** `feat(platform): deploy table maintenance control plane chart`.

### Task 19: End-to-end verification and ADRs

**Files:**
- Create `platform/25-lakehouse-control-plane/e2e.sh` (manual check, not wired into `validate`), `docs/adr/0001-table-identity-by-iceberg-uuid.md`, `docs/adr/0002-entity-workflow-per-table.md`, `docs/adr/0003-events-as-hints-catalog-as-truth.md`
- Modify `platform/25-lakehouse-control-plane/README.md`, `CLAUDE.md`

**Interfaces:**
- `e2e.sh` (uses `kubectl port-forward` in the background with cleanup chained after `__log::on_exit`, or `kubectl exec` + `curl` inside the api pod):
  1. `POST /v1/discovery-rules` INCLUDE `iceberg / e2e / tm_e2e_*` with the `default` template, priority 10.
  2. Via the Trino CLI (client cert from `task trino:issue-cert`): create `iceberg.e2e.tm_e2e_orders` partitioned by `day(order_ts)` and `bucket(4, id)`, run ≥ 20 single-row `INSERT`s, plus a `DELETE` to create delete files.
  3. Poll `GET /v1/tables?status=ACTIVE` until the table appears (≤ 15 min, covering the 10-min discovery fallback).
  4. `PUT /v1/tables/{uuid}/settings` lowering thresholds (`min_reducible_files: 2`, `min_small_manifests: 1`, `expire_snapshots.older_than_seconds: 60`, `retain_last: 1`, `remove_orphan_files.older_than_seconds: 86400`) and `POST /v1/tables/{uuid}/maintenance` with all four operations.
  5. Poll `GET /v1/tables/{uuid}/runs` until the run is terminal; require every operation `SUCCEEDED` and `rewritten_data_files_count > 0`.
  6. Compare RustFS object listings of the table's data prefix (via the `pgsty/mc` image as a one-off pod) and Trino `SELECT count(*) FROM "tm_e2e_orders$files"` before/after: file count decreased; `$snapshots` count decreased.
  7. Leave the scheduled path running and confirm in the Temporal Web UI (port-forward `temporal-web:8080`) that `table-reconcile-{uuid}` exists.
- ADRs: short, in the existing ADR style (context, considered options, decision, consequences), one decision each.

- [ ] **Step 1:** Write `e2e.sh`; run it against the cluster with `KUBE_CONTEXT=retail-lakehouse`; capture the before/after numbers.
- [ ] **Step 2:** Write the three ADRs; update README (how to use the API, e2e instructions) and `CLAUDE.md` (initiative done, follow-ups found during e2e).
- [ ] **Step 3: Commit** `docs(table-maintenance): add e2e check and control plane ADRs`.
