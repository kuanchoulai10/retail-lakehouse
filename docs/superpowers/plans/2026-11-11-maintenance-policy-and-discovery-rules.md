# Maintenance Policies and Discovery Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace presets, per-table settings, manual table selection and the discovery switch with discovery rules (which tables are managed, re-applied every pass) and inheritable, versioned maintenance policies (how a managed table is maintained).

**Architecture:** Three new aggregates in the table-maintenance context: `TableMaintenancePolicy` (with immutable versions), `TableMaintenancePolicyAttachment` (one per target) and `TableDiscoveryRules` (the singleton ordered rule list). The plan activity resolves the applicable policy on every reconciliation; assessment and procedure arguments read the policy's trigger and execution policies. New code lands beside the old, consumers switch, then the old code is deleted, so every commit stays green.

**Tech Stack:** Python 3.14, Pydantic v2 domain (`base.ValueObject` and friends), FastAPI, SQLAlchemy, Temporal, React + Orval-generated client, Storybook/vitest.

**Spec:** `docs/superpowers/specs/2026-11-11-maintenance-policy-and-discovery-rules-design.md`

## Global Constraints

- Paths: backend root `src/data-platform/backend`; `C/` = `context/table_maintenance/`, `D/` = `C/application/domain/model/`, `DS/` = `C/application/domain/service/`, `P/` = `C/application/port/`, `S/` = `C/application/service/`, `AW/` = `C/adapter/inbound/web/`, `AS/` = `C/adapter/outbound/`, `T/` = `C/adapter/hybrid/temporal/`, `TT/` = `tests/context/table_maintenance/`. Frontend root `src/data-platform/frontend/src`.
- No data migration, ever. Schema comes from `metadata.create_all`; the cluster is rebuilt.
- One object per file; `from __future__ import annotations`; ABC not Protocol; StrEnum; TDD (failing test first, RED captured).
- Domain and `base` import only stdlib, `base`, own-context domain, `pydantic`, `pydantic_core`, `annotated_types`. Services, ports and exceptions never import pydantic.
- `ValueObject`: frozen, strict, `extra="forbid"`; wire input via `from_primitives`, output via `to_primitives`; whole-second durations use `WholeSeconds` with `validation_alias`/`serialization_alias` `<name>_seconds`.
- **Inheritance depth for domain primitives is 1** (`tests/architecture/test_inheritance_depth.py`). Per-operation trigger policies are therefore parametrizations, not subclasses: `RewriteDataFilesTriggerPolicy = TriggerPolicy[RewriteDataFilesConditions]`, one alias per file. Execution policies and `RewriteDataFilesPolicy` subclass `ValueObject` directly.
- Every aggregate needs its directory in every layer (`tests/architecture/test_aggregate_axis.py`); a task that adds an aggregate root adds all its layers.
- Broken invariant → 422 one-line message; conflict (stale version, delete attached/default, duplicate name) → 409; missing → 404.
- A task that changes the HTTP API regenerates `backend/openapi.json` (`bootstrap/export_openapi.py`) and the client (`task dev:generate-api`), and keeps the console compiling and its tests green: UI that used a removed endpoint is removed in that task; new UI arrives in Tasks 11–13.
- Before each commit: backend `pytest -v`, `ty check`, `ruff check .`, `ruff format --check .`, `lint-imports` via `uv run --project src/data-platform/backend --directory src/data-platform/backend …`; frontend (when touched) `npm --prefix src/data-platform/frontend run test -- --run`, `run test:stories`, `run lint`, `run typecheck`.
- Commits: explicit paths, conventional lowercase subjects as given, message ends with a blank line and `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- Vocabulary: "policy" means maintenance policy only; "discovery rules"; verb "discover tables". UI copy follows `src/data-platform/frontend/CLAUDE.md`.
- Do not touch `platform/30-thanos`, `platform/24-e2e-validation`, the ArgoCD path, `.claude/worktrees/`, `src/data-platform/frontend/src/stories/mockups/`.

## Review Focus

1. A rule list saved with two equal priorities → 422 and nothing saved, no discovery started (Task 8).
2. A table in `prod.sales.eu` with attachments on catalog `prod`, namespace `prod.sales` → `prod.sales` applies; with one on the table too → the table's applies; a `default` attachment on `prod.sales` overrides the catalog's (Task 3).
3. A renamed table keeps its table-level attachment (keyed by UUID) while its namespace-level policy follows the new name (Task 3).
4. Deleting an attached policy or `default` → 409; attaching to a catalog, namespace or table missing from the catalog → 404 (Tasks 2, 9).
5. A stale `version` on `PUT /maintenance-policies/{name}` or `PUT /discovery-rules` → 409 and no change (Tasks 2, 8, 9).

---

### Task 1: Maintenance policy value objects

**Files:**
- Create in `D/table_maintenance_policy/`: `at_least.py`, `small_manifests_condition.py`, `partial_progress.py`, `rewrite_data_files_conditions.py`, `rewrite_manifests_conditions.py`, `expire_snapshots_conditions.py`, `remove_orphan_files_conditions.py`, `trigger_policy.py`, `rewrite_data_files_trigger_policy.py`, `rewrite_manifests_trigger_policy.py`, `expire_snapshots_trigger_policy.py`, `remove_orphan_files_trigger_policy.py`, `rewrite_data_files_execution_policy.py`, `rewrite_manifests_execution_policy.py`, `expire_snapshots_execution_policy.py`, `remove_orphan_files_execution_policy.py`, `compaction_unit.py`, `compaction_scope.py`, `operation_policy.py`, `rewrite_data_files_policy.py`, `rewrite_manifests_policy.py`, `expire_snapshots_policy.py`, `remove_orphan_files_policy.py`, `operation_policies.py`, `maintenance_policy_content.py`, `__init__.py`
- Test: `TT/application/domain/model/table_maintenance_policy/test_maintenance_policy_content.py`, `test_conditions.py`

**Interfaces:**
- Produces:
  - `AtLeast(at_least: PositiveInt)`; `SmallManifestsCondition(at_least: PositiveInt, smaller_than_bytes: PositiveInt | None = None)`; `PartialProgress(enabled: bool, max_commits: PositiveInt | None = None)`.
  - `Conditions` is not a class; each conditions model subclasses `ValueObject` directly: `RewriteDataFilesConditions(reducible_files: AtLeast | None = None)`, `RewriteManifestsConditions(small_manifests: SmallManifestsCondition | None = None)`, `ExpireSnapshotsConditions(expirable_snapshots: AtLeast | None = None)`, `RemoveOrphanFilesConditions()`. Each has `def is_empty(self) -> bool`.
  - `TriggerPolicy[C](ValueObject)`: `cooldown: WholeSeconds` (alias `cooldown_seconds`), `conditions: C`. Aliases `RewriteDataFilesTriggerPolicy = TriggerPolicy[RewriteDataFilesConditions]` etc.
  - `RewriteDataFilesExecutionPolicy(target_file_size_bytes: PositiveInt | None = None, min_input_files: PositiveInt, partial_progress: PartialProgress)`; `RewriteManifestsExecutionPolicy()`; `ExpireSnapshotsExecutionPolicy(older_than: WholeSeconds /* older_than_seconds */, retain_last: PositiveInt)`; `RemoveOrphanFilesExecutionPolicy(older_than: WholeSeconds /* older_than_seconds */)` keeping today's ≥ 1 day validator from `remove_orphan_files_settings.py`.
  - `CompactionUnit(StrEnum)`: `PARTITION = "partition"`, `TABLE = "table"`; `CompactionScope(unit: CompactionUnit)` (new VO in this package; the old enum in `D/shared/compaction_scope.py` stays until Task 7).
  - `OperationPolicy[T, E](ValueObject)`: `enabled: bool`, `trigger_policy: T`, `execution_policy: E`; aliases `RewriteManifestsPolicy`, `ExpireSnapshotsPolicy`, `RemoveOrphanFilesPolicy`. `RewriteDataFilesPolicy(ValueObject)`: `enabled`, `scope: CompactionScope`, `trigger_policy: RewriteDataFilesTriggerPolicy`, `execution_policy: RewriteDataFilesExecutionPolicy`.
  - `OperationPolicies(rewrite_data_files, rewrite_manifests, expire_snapshots, remove_orphan_files)` with `def for_operation(self, op: MaintenanceOperation) -> RewriteDataFilesPolicy | RewriteManifestsPolicy | ExpireSnapshotsPolicy | RemoveOrphanFilesPolicy`.
  - `MaintenancePolicyContent(description: str, reconcile_interval: WholeSeconds /* reconcile_interval_seconds */, dry_run: bool, operations: OperationPolicies)` with `@classmethod def platform_default(cls) -> MaintenancePolicyContent` returning the spec's default values (description `"Platform default"`).

- [ ] **Step 1: Write the failing tests**

```python
def test_platform_default_round_trips_to_spec_json():
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    assert wire["reconcile_interval_seconds"] == 3600 and wire["dry_run"] is False
    rdf = wire["operations"]["rewrite_data_files"]
    assert rdf["scope"] == {"unit": "partition"}
    assert rdf["trigger_policy"] == {"cooldown_seconds": 3600, "conditions": {"reducible_files": {"at_least": 5}}}
    assert rdf["execution_policy"] == {"target_file_size_bytes": None, "min_input_files": 2, "partial_progress": {"enabled": True, "max_commits": None}}
    assert wire["operations"]["rewrite_manifests"]["trigger_policy"]["conditions"] == {"small_manifests": {"at_least": 5, "smaller_than_bytes": None}}
    assert wire["operations"]["expire_snapshots"]["trigger_policy"] == {"cooldown_seconds": 21600, "conditions": {"expirable_snapshots": {"at_least": 1}}}
    assert wire["operations"]["expire_snapshots"]["execution_policy"] == {"older_than_seconds": 86400, "retain_last": 10}
    assert wire["operations"]["remove_orphan_files"] == {"enabled": True, "trigger_policy": {"cooldown_seconds": 604800, "conditions": {}}, "execution_policy": {"older_than_seconds": 259200}}
    assert MaintenancePolicyContent.from_primitives(wire) == MaintenancePolicyContent.platform_default()

def test_condition_of_another_operation_is_rejected():
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["rewrite_manifests"]["trigger_policy"]["conditions"]["reducible_files"] = {"at_least": 5}
    with pytest.raises(ValidationError):
        MaintenancePolicyContent.from_primitives(wire)

def test_missing_condition_means_empty():
    assert RewriteDataFilesConditions().is_empty() and not RewriteDataFilesConditions(reducible_files=AtLeast(at_least=1)).is_empty()

def test_orphan_older_than_below_one_day_is_rejected(): ...  # 86399 → ValidationError
def test_at_least_zero_is_rejected(): ...                     # {"at_least": 0} → ValidationError
```

- [ ] **Step 2: Run** `pytest TT/application/domain/model/table_maintenance_policy -v` — Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** the files above. `None` fields serialise as `null` (no `exclude_none`), matching the spec JSON.
- [ ] **Step 4: Run** the tests, then the full backend check list — Expected: PASS (no aggregate root yet, so the axis test is unaffected).
- [ ] **Step 5: Commit** `feat(table-maintenance): maintenance policy value objects`

### Task 2: `TableMaintenancePolicy` aggregate with versions, repository, use cases and default seed

**Files:**
- Create: `D/table_maintenance_policy/table_maintenance_policy.py`, `table_maintenance_policy_name.py` (EntityId, pattern `^[A-Za-z0-9_-]{1,64}$`), `table_maintenance_policy_version.py` (VO: `name`, `version: PositiveInt`, `content`, `created_at`), `default_policy_name.py` (`DEFAULT_POLICY_NAME = "default"`)
- Create ports: `P/outbound/table_maintenance_policy/table_maintenance_policies_repo.py`; inbound use cases under `P/inbound/table_maintenance_policy/`: `create_table_maintenance_policy`, `get_table_maintenance_policy`, `get_table_maintenance_policy_version`, `list_table_maintenance_policies`, `update_table_maintenance_policy`, `delete_table_maintenance_policy`, `ensure_default_table_maintenance_policy`
- Create services `S/table_maintenance_policy/<same names>.py` and `table_maintenance_policy_output_fields.py`
- Create SQL `AS/table_maintenance_policy/sql/{table_maintenance_policies_table,table_maintenance_policy_versions_table,table_maintenance_policies_sql_repo,table_maintenance_policy_row_mapper}.py`; add the package to `AGGREGATE_SQL_PACKAGES` in `AS/shared/sql/create_schema.py`
- Create fake `TT/fakes/in_memory_table_maintenance_policies_repo.py`
- Modify `bootstrap/container/{repositories,build_repositories,use_cases,build_use_cases,run_migrations}.py` (call `ensure_default_table_maintenance_policy` after `create_schema`, beside the preset seed until Task 7)
- Tests: `TT/application/domain/model/table_maintenance_policy/test_table_maintenance_policy.py`, `TT/application/service/table_maintenance_policy/test_table_maintenance_policy_services.py`, `TT/adapter/outbound/table_maintenance_policy/test_table_maintenance_policies_sql_repo.py`, `tests/bootstrap/container/test_run_migrations.py`

**Interfaces:**
- Consumes: `MaintenancePolicyContent` (Task 1).
- Produces:
  - `TableMaintenancePolicy(AggregateRoot[TableMaintenancePolicyName])`: `id`, `content`, `version: PositiveInt`, `created_at`, `updated_at`; `@classmethod create(name, content, now)` (version 1); `def replace(self, content, expected_version: int, now) -> None` raising `StalePolicyVersion` (new domain exception in the package, mapped to 409 by `translate_domain_errors`) when `expected_version != version`, else version += 1; `def current_version(self) -> TableMaintenancePolicyVersion`; `@property is_default`.
  - `TableMaintenancePoliciesRepo(Repository)`: `create`, `update` (writes the new version row in the same transaction), `get(name) -> TableMaintenancePolicy | None`, `get_version(name, version) -> TableMaintenancePolicyVersion | None`, `list_all()`, `delete(name)` (deletes versions too).
  - Use-case inputs/outputs carry primitives: `content: dict[str, Any]`, `version: int`. Delete answers `ConflictError` for `default`; "attached" is checked in Task 3 once attachments exist (this task leaves a `has_attachments` hook out; Task 3 adds it to the delete service).
  - `EnsureDefaultTableMaintenancePolicyUseCase.execute()` creates `default` with `MaintenancePolicyContent.platform_default()` when missing; idempotent.

- [ ] **Step 1: Failing tests** — `test_replace_increments_version_and_keeps_old_version_readable` (create v1, replace with expected 1 → v2; `repo.get_version(name, 1).content` equals the original); `test_replace_with_stale_version_conflicts` (expected 1 after v2 → `ConflictError` from the service, repo unchanged); `test_duplicate_name_conflicts`; `test_invalid_name_is_422` (`"has space"`); `test_delete_default_conflicts`; `test_ensure_default_is_idempotent` (twice → one policy, version 1); SQL repo round-trip of a policy and two versions on the sqlite fixture; `test_run_migrations_seeds_default_policy`.
- [ ] **Step 2: Run** them — Expected: FAIL.
- [ ] **Step 3: Implement.** Store content as one JSON column per version row (`content_json`) and the current version number on the policy row.
- [ ] **Step 4: Run** the full backend check list — Expected: PASS, including `test_aggregate_axis.py`.
- [ ] **Step 5: Commit** `feat(table-maintenance): versioned maintenance policy aggregate`

### Task 3: Attachments and applicable-policy resolution

**Files:**
- Create domain `D/table_maintenance_policy_attachment/`: `policy_target_type.py` (StrEnum `catalog`, `namespace`, `table`), `policy_target.py`, `table_maintenance_policy_attachment_id.py`, `table_maintenance_policy_attachment.py`
- Create `DS/table_maintenance_policy_attachment/candidate_policy_targets.py`
- Create ports `P/outbound/table_maintenance_policy_attachment/table_maintenance_policy_attachments_repo.py`; inbound `P/inbound/table_maintenance_policy_attachment/{attach_table_maintenance_policy,detach_table_maintenance_policy,list_table_maintenance_policy_attachments,resolve_applicable_table_maintenance_policy}/`
- Create services `S/table_maintenance_policy_attachment/<same names>.py`; modify `S/table_maintenance_policy/delete_table_maintenance_policy.py` (409 when attached)
- Create SQL `AS/table_maintenance_policy_attachment/sql/{…_table,…_sql_repo,…_row_mapper}.py`; register in `create_schema.py`; fake `TT/fakes/in_memory_table_maintenance_policy_attachments_repo.py`; wire in bootstrap
- Tests: `TT/application/domain/service/table_maintenance_policy_attachment/test_candidate_policy_targets.py`, `TT/application/service/table_maintenance_policy_attachment/test_attachment_services.py`, SQL repo test

**Interfaces:**
- Produces:
  - `PolicyTarget(type: PolicyTargetType, path: tuple[str, ...], table_uuid: str | None = None)`; validator: `table_uuid` set iff `type == table`; path length 1 for catalog, ≥ 2 for namespace and table. `def attachment_id(self) -> TableMaintenancePolicyAttachmentId` = `"table:" + table_uuid` for tables, else `f"{type}:" + "\x1f".join(path)`.
  - `TableMaintenancePolicyAttachment(AggregateRoot[...Id])`: `target`, `policy_name`, `attached_at`; `attach(target, policy_name, now)`; `def replace_policy(self, policy_name, now)`.
  - `candidate_policy_targets(name: TableName, table_uuid: str) -> tuple[PolicyTarget, ...]`: table first, then each namespace prefix from deepest to shallowest (`TableName.namespace` split on `.`), then the catalog.
  - `ResolveApplicableTableMaintenancePolicyUseCase`: input `table_uuid: str | None, catalog: str, namespace: str | None, table: str | None`; output `policy_name, version, content: dict, target: dict | None` (`None` = default fallback). For a catalog or namespace target the candidates start at that target.
  - Attach validates the target exists through the existing `ReadTableMetadataGateway` (catalog listed, namespace listed, table loads) → `NotFoundError`; validates the policy exists → `NotFoundError`. `default` may be attached.

- [ ] **Step 1: Failing tests** — Review Focus 2 and 3 as `test_deepest_attachment_wins`, `test_table_attachment_beats_namespace`, `test_default_attachment_overrides_catalog_attachment`, `test_rename_keeps_table_attachment_and_follows_namespace`; `test_no_attachment_falls_back_to_default` (`target is None`, `policy_name == "default"`); `test_attach_replaces_existing_attachment_on_target`; `test_attach_to_missing_namespace_is_404`; `test_delete_attached_policy_conflicts`.
- [ ] **Step 2–4:** RED, implement, full checks GREEN.
- [ ] **Step 5: Commit** `feat(table-maintenance): policy attachments and applicable policy`

### Task 4: Assessment and procedure arguments read the policy

**Files:**
- Modify: `DS/table/assess_maintenance.py`, `DS/shared/resolve_target_file_size.py`, `S/table_maintenance_run/maintenance_procedure_args.py`, `S/table/plan_table_maintenance.py`, `D/shared/operation_assessment.py` (drop `combine`), `AS/table_reconciliation/sql/table_reconciliation_row_mapper.py` (drop `combine`), `bootstrap/container/build_use_cases.py`
- Delete: `D/shared/condition_combine.py` and its re-export
- Tests: `TT/application/domain/service/table/test_assess_maintenance.py`, `TT/application/service/table_maintenance_run/test_table_maintenance_run_services.py` (procedure args), `TT/application/service/table/test_plan_table_maintenance_service.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `assess_maintenance(table: Table, policy: MaintenancePolicyContent, observation: TableObservation, now: datetime) -> MaintenanceAssessment`. Due = enabled and cooldown (with today's failure backoff) passed and (conditions empty or any condition holds). Measurements keep their keys (`reducible_files`, `small_manifests`, `target_file_size`, `qualifying_partitions`) and add `expirable_snapshots`.
  - `resolve_target_file_size(properties: dict[str, str]) -> int` (table property, else 512 MiB) for measuring; `resolve_execution_target_file_size(policy: RewriteDataFilesExecutionPolicy, properties) -> int` for the procedure.
  - `maintenance_procedure_args(operation, policy: MaintenancePolicyContent, properties, now) -> dict[str, Any]`: rewrite data files → `{"target-file-size-bytes": …, "min-input-files": policy min_input_files, "partial-progress.enabled": …}` plus `"partial-progress.max-commits"` when set; others as today from the execution policies.
  - `PlanTableMaintenanceService` gains the resolve use case (constructor arg `resolve_applicable_policy`), resolves on every plan, and its output gains `policy_name: str, policy_version: int, policy_target: dict | None`. `reconcile_interval_seconds` and `dry_run` come from the policy. Table `settings` is no longer read here; a table with `settings is None` still plans (status gating unchanged until Task 6).

- [ ] **Step 1: Failing tests** — `test_any_condition_holding_makes_operation_due` (exercise the OR helper the assessment uses, `any_condition_holds(measurements: Sequence[Measurement]) -> bool` in `DS/table/any_condition_holds.py`, with one failing and one holding measurement → True, both failing → False, none → False); `test_due_when_reducible_files_reaches_threshold` and its negative; `test_empty_conditions_due_after_cooldown` (remove orphan files); `test_expire_snapshots_not_due_without_expirable_snapshot`; `test_reducible_files_measured_with_table_property_not_execution_value` (execution 1 GiB, property 128 MiB → measurement `target_file_size` observed 134217728); `test_procedure_args_take_min_input_files_and_partial_progress_from_policy` (min_input_files 7, max_commits 3 → `"min-input-files": 7, "partial-progress.max-commits": 3`); `test_plan_output_names_resolved_policy` (namespace attachment → `policy_target == {"type": "namespace", "path": [...]}`).
- [ ] **Step 2–4:** RED, implement, full checks GREEN. Existing assessment tests are rewritten to build `MaintenancePolicyContent` instead of `MaintenanceSettings`; their expected measurements stay the same.
- [ ] **Step 5: Commit** `refactor(table-maintenance): assess and plan from the applicable policy`

### Task 5: Reconciliation records name the policy

**Files:**
- Modify: `D/table_reconciliation/table_reconciliation.py`, `P/inbound/table_reconciliation/record_table_reconciliation/*`, `S/table_reconciliation/record_table_reconciliation.py`, `AS/table_reconciliation/sql/{table_reconciliations_table,table_reconciliation_row_mapper}.py`, `T/inbound/activities/table_reconciliation_activities.py`, `T/inbound/workflows/table_reconciliation_workflow.py` (pass the plan's policy fields to the record activity), `AW/table_reconciliation/dto.py`, `backend/openapi.json`, generated client
- Tests: `TT/application/domain/model/table_reconciliation/test_table_reconciliation.py`, record service test, SQL repo test, `TT/adapter/hybrid/temporal/inbound/test_table_reconciliation_workflow.py`, `TT/adapter/inbound/web/table_reconciliation/test_table_reconciliation_routes.py`

**Interfaces:**
- Produces: `TableReconciliation` fields `policy_name: str`, `policy_version: PositiveInt`, `policy_target: PolicyTarget | None`; API response fields `policy_name`, `policy_version`, `policy_target` (`{"type", "path"}` or null).

- [ ] **Step 1: Failing tests** — `test_record_keeps_policy_name_version_and_target`; workflow test asserting the record activity receives the plan's `policy_name`/`policy_version`/`policy_target`; route test asserting the three fields in the JSON.
- [ ] **Step 2–4:** RED, implement, regenerate OpenAPI and client, full checks GREEN.
- [ ] **Step 5: Commit** `feat(table-maintenance): reconciliations record the policy used`

### Task 6: Tables are managed or unmanaged; manual selection goes away

**Files:**
- Modify: `D/table/{table,table_status,table_change}.py`; delete `D/table/table_selection.py`
- Delete services, ports, routes and tests for `pause_table`, `resume_table`, `include_table`, `exclude_table`, `reset_table_selection`, `update_table_settings`
- Modify: `S/table/{register_discovered_table,sync_discovered_tables,process_table_hint,get_table_health,plan_table_maintenance,table_output_fields,list_tables}.py`, `AS/table/sql/{tables_table,table_row_mapper}.py` (drop `settings_json`, `selection`, `source_preset_id`), `AW/table/{router,dto}.py`, `T/contracts/table_reconciliation/signal.py`, `T/outbound/table/send_table_change_temporal_gateway.py`, `D/table_reconciliation/wake_reason.py`, `T/inbound/workflows/table_reconciliation_workflow.py`, bootstrap wiring
- Frontend: remove pause/resume (`components/TableHeader.tsx`), settings editing (`components/SettingsForm.tsx`, `SettingsFieldGroup.tsx`, `tabs/SettingsTab.tsx` — the tab is removed), include/exclude affordances, `lib/tableMaintenanceState.ts` paused/excluded states, `reconciliationText.ts` paused text; update `stories/storyData.ts`, `test/fixtures.ts`; regenerate client
- Tests: `TT/application/domain/model/table/test_table.py`, `TT/application/service/table/test_discovery_sync_services.py`, `test_table_services.py`, workflow and gateway tests, web route tests, `tests/architecture` as needed, console tests and stories

**Interfaces:**
- Produces:
  - `TableStatus`: `MANAGED`, `UNMANAGED`, `DROPPED`. `Table` fields: `id`, `name`, `status`, `matched_rule_id`, `registered_at`, `updated_at`, `operation_states`. Methods `register(id, name, rule_id, now)` (MANAGED), `manage(rule_id, now)`, `unmanage(now)`, `mark_dropped(now)`, `rename(name, now)`, `record_operation_result(...)`, `is_managed` property (replaces `is_enrolled`).
  - `TableChange`: `UPDATED`, `POLICY_CHANGED`, `STOPPED`, `MAINTENANCE_REQUESTED`, `RECONCILE_REQUESTED`, `SEEN`. Signal `SETTINGS_CHANGED` → `POLICY_CHANGED` (wire name `policy_changed`); `PAUSE`, `RESUME` removed. `WakeReason`: `SETTINGS_CHANGED` → `POLICY_CHANGED`; `PAUSED`, `RESUMED` removed. The workflow's `_ENDING_REASONS` becomes `{"dropped", "unmanaged"}` and the plan's skip reason `excluded` becomes `unmanaged`.
  - Discovery applies the spec's five per-table steps, deciding with `match_table_discovery_rule` over the existing rule aggregate (its `preset_id` is ignored from now on). `register_discovered_table` no longer takes the presets repo.

- [ ] **Step 1: Failing tests** — `test_known_managed_table_becomes_unmanaged_when_rule_excludes_it` (STOPPED sent, status UNMANAGED); `test_unmanaged_table_is_managed_again_when_rule_includes_it` (status MANAGED, change sent with `is_managed` so the gateway signal-with-starts); `test_namespace_pass_never_unmanages_missing_tables`; `test_unmanaged_reason_ends_workflow_after_in_flight_run` (workflow test: a plan answering `unmanaged` while a run is in flight ends only after `maintenance_finished`); route tests that `/pause`, `/resume`, `/include`, `/exclude`, `/reset-selection`, `PUT /settings` answer 404/405.
- [ ] **Step 2–4:** RED, implement, regenerate OpenAPI and client, adjust the console, full backend and frontend checks GREEN.
- [ ] **Step 5: Commit** `refactor(table-maintenance): discovery rules alone decide managed tables`

### Task 7: Delete presets and `MaintenanceSettings`

**Files:**
- Delete: `D/table_maintenance_preset/`, `P/{inbound,outbound}/table_maintenance_preset/`, `S/table_maintenance_preset/`, `AS/table_maintenance_preset/`, `AW/table_maintenance_preset/`, `TT/fakes/in_memory_table_maintenance_presets_repo.py`, all preset tests, `bootstrap/container/seed_default_preset.py`; `D/shared/{maintenance_settings,rewrite_data_files_settings,rewrite_manifests_settings,expire_snapshots_settings,remove_orphan_files_settings,compaction_scope}.py` and their tests; rule `preset_id` (model, mapper, table, DTO, services)
- Modify: `AS/shared/sql/create_schema.py`, `AW/register_routes.py`, `bootstrap/container/*`, `platform/25-lakehouse-control-plane/chart/templates/_helpers.tpl` (init wait polls `table_maintenance_policies` for `name = 'default'`)
- Frontend: delete `pages/PresetsPage.*`, the `/presets` route and nav link, preset links in `DiscoveryRulesPage`, preset story handlers and data; regenerate client

- [ ] **Step 1: Failing tests** — extend `tests/bootstrap/container/test_run_migrations.py` with `test_schema_has_no_preset_table` (`inspect(engine).get_table_names()` lacks `table_maintenance_presets`) and route test `GET /v1/table-maintenance-presets` → 404.
- [ ] **Step 2–4:** RED, delete and rewire, `rg -n "Preset|MaintenanceSettings|preset_id" src/data-platform` returns only unrelated hits, full checks GREEN.
- [ ] **Step 5: Commit** `refactor(table-maintenance): remove presets and maintenance settings`

### Task 8: `TableDiscoveryRules` aggregate, whole-list save, discover on save, preview

**Files:**
- Create `D/table_discovery_rules/`: `rule_action.py` (StrEnum `include`, `exclude`), `glob_list.py` (VO: non-empty `tuple[str, ...]`, `matches(value) -> bool` with `fnmatch.fnmatchcase`), `table_discovery_rule.py` (Entity: `id`, `priority: int`, `action`, `enabled`, `catalogs`, `namespaces`, `tables`, timestamps; `matches(name: TableName) -> bool`), `table_discovery_rule_id.py`, `table_discovery_rules_id.py` (singleton `"global"`), `table_discovery_rules.py` (AggregateRoot: `rules: tuple[TableDiscoveryRule, ...]`, `version`; `replace(rules, expected_version, now)`; `decide(name) -> TableDiscoveryRule | None` = first enabled match by priority)
- Create ports `P/inbound/table_discovery_rules/{get_table_discovery_rules,replace_table_discovery_rules,preview_table_discovery_rules}/`, `P/outbound/table_discovery_rules/table_discovery_rules_repo.py`; services `S/table_discovery_rules/*`; SQL `AS/table_discovery_rules/sql/*`; router `AW/table_discovery_rules/{router,dto}.py` at `/v1/discovery-rules`
- Delete: `D/table_discovery_rule/`, `DS/table_discovery_rule/`, `D/table_discovery_settings/`, their ports, services, SQL, routers (`/table-discovery-rules`, `/table-discovery-settings` incl. `/catalogs` and `/scan`), fakes, tests; `P/outbound/table_discovery_settings/update_table_discovery_schedule/` and `T/outbound/table_discovery_settings/`
- Keep and move: covered catalogs become `GET /v1/discovery-rules/catalogs` served by a `list_covered_catalogs` use case under `table_discovery_rules`; `SendDiscoveryRequestGateway` is reused to discover tables after a save
- Modify: `S/table/{sync_discovered_tables,process_table_hint,register_discovered_table}.py` (decide via `TableDiscoveryRules.decide`), `bootstrap/container/apply_worker_startup.py` (schedule never paused), `T/inbound/ensure_table_discovery_schedule.py` (drop `paused`), bootstrap wiring, `create_schema.py`, `register_routes.py`
- Frontend: `pages/DiscoveryRulesPage.tsx` reads the new endpoint (read-only list, as today, until Task 11); remove the discovery switch; regenerate client; update stories and tests

**Interfaces:**
- Produces:
  - `GET /v1/discovery-rules` → `{"version": int, "rules": [rule…]}`; `PUT /v1/discovery-rules` body `{"version": int, "rules": [{"id"?: str, "priority", "action", "enabled", "catalogs", "namespaces", "tables"}]}` → 200 with the saved list; rules without `id` get one; after commit, one `SendDiscoveryRequestGateway.send` per covered catalog.
  - `POST /v1/discovery-rules/preview` body `{"rules": [...]}` → `{"tables": [{"catalog", "namespace", "table", "rule_id": str | null, "managed": bool}], "managed": int, "unmanaged": int}`; reads every covered catalog via `ReadTableMetadataGateway.list_tables`, writes nothing. Unsaved rules are identified by their list index in `rule_id` as `"#<index>"` when they have no id.

- [ ] **Step 1: Failing tests** — Review Focus 1 `test_equal_priorities_rejected_and_nothing_saved_or_discovered`; Review Focus 5 `test_stale_version_conflicts`; `test_any_glob_in_field_matches_and_all_fields_must_match`; `test_namespace_glob_matches_full_dotted_name` (`prod.*` matches `prod.sales`); `test_disabled_rule_skipped`; `test_save_discovers_each_covered_catalog_once`; `test_preview_reports_deciding_rule_and_writes_nothing`; `test_old_discovery_endpoints_are_gone`; `test_worker_startup_never_pauses_schedule`.
- [ ] **Step 2–4:** RED, implement, regenerate OpenAPI and client, full checks GREEN.
- [ ] **Step 5: Commit** `feat(table-maintenance): discovery rules saved whole, with preview`

### Task 9: Maintenance policy HTTP API and wake-ups

**Files:**
- Create `AW/table_maintenance_policy/{router,dto}.py` (`/v1/maintenance-policies`), `AW/table_maintenance_policy_attachment/{router,dto}.py` (`/v1/maintenance-policies/{name}/mappings`, `/v1/tables/{table_uuid}/applicable-policy`, `/v1/applicable-policy`)
- Create `S/table_maintenance_policy_attachment/notify_policy_change.py` (helper used by update, attach and detach services)
- Modify: `AW/register_routes.py`, `AW/shared/web_use_cases.py`, bootstrap wiring, `backend/openapi.json`, generated client
- Tests: `TT/adapter/inbound/web/table_maintenance_policy/test_table_maintenance_policy_routes.py`, `.../table_maintenance_policy_attachment/test_attachment_routes.py`, `TT/application/service/table_maintenance_policy_attachment/test_notify_policy_change.py`

**Interfaces:**
- Produces: the spec's API table exactly; `PUT /maintenance-policies/{name}` body `{"version": int, ...content}`; mappings `PUT` and `DELETE` body `{"target": {"type", "path"}}` (table path `[catalog, ns…, table]`, resolved to the UUID through the catalog gateway). `GET …/mappings` items carry `orphaned: bool`, true when the target is no longer in the catalog. Before writing the mapping endpoints, check Polaris's policy-mapping and applicable-policies request shapes (Polaris docs in the spec's References) and follow them where they fit; record any deviation in the task report.
- After a policy update, attach or detach, `notify_policy_change` sends `TableChange.POLICY_CHANGED` for every managed table whose resolved policy (name or version) changed.

- [ ] **Step 1: Failing tests** — Review Focus 4 and 5 as route tests (`DELETE` attached → 409, `DELETE /default` → 409, attach to missing table → 404, stale `PUT` → 409); `test_get_old_version_after_update`; `test_attach_wakes_only_tables_whose_policy_changed` (two tables in different namespaces, attach to one namespace → one `POLICY_CHANGED`); `test_update_default_wakes_tables_without_attachment`.
- [ ] **Step 2–4:** RED, implement, regenerate, full checks GREEN.
- [ ] **Step 5: Commit** `feat(table-maintenance): maintenance policy api`

### Task 10: Ops scripts and docs for the new API

**Files:**
- Modify: `platform/25-lakehouse-control-plane/{README.md,e2e.sh,validate.sh}` (replace preset, discovery-settings, pause/resume and table-settings calls with discovery-rules `PUT`, policy create/attach and applicable-policy checks), `docs/istio/gateway-api.md` example path, `src/data-platform/backend/CLAUDE.md` (aggregates, DTO example names, contract count if changed), root `CLAUDE.md` Project Vision aggregate list (`Table`, `TableMaintenancePolicy`, `TableMaintenancePolicyAttachment`, `TableDiscoveryRules`, `TableMaintenanceRun`, `TableReconciliation`), `docs/agents/known-follow-ups.md` (drop the default-preset and discovery-switch items; add "execution `target_file_size_bytes` can disagree with the measured target size"), `src/data-platform/frontend/CLAUDE.md` (MaintenanceEmptyState reasons)
- Test: `shellcheck` via pre-commit; `bash -n` on both scripts.

- [ ] **Step 1:** Edit; **Step 2:** `pre-commit run --all-files` and `bash -n` pass; **Step 3: Commit** `docs(table-maintenance): ops scripts and docs for policies and discovery rules`

### Task 11: Console — Discovery rules editor with preview

**Files:**
- Modify: `pages/DiscoveryRulesPage.tsx` (+ `.test.tsx`, `.stories.tsx`)
- Create: `components/DiscoveryRuleEditor.tsx`, `components/DiscoveryRulesPreview.tsx`, `components/GlobListField.tsx` (+ tests, stories)
- Modify: `stories/storyData.ts`, `stories/lakehouseHandlers.ts`

**Interfaces:**
- Consumes: generated hooks for `GET`/`PUT /discovery-rules` and `POST /discovery-rules/preview`.
- Behaviour: the page holds a draft copy of the list; add, edit (dialog with priority, action, enabled, three glob-chip fields), delete and reorder change only the draft; the preview panel calls preview on draft changes (debounced 300 ms) and groups tables by deciding rule with managed/unmanaged counts; "Save" sends one `PUT` with the read `version`, then shows "Saved. Discovering tables…"; a 409 shows "Someone else changed these rules. Reload to see their version." and keeps the draft; "Discard changes" restores the saved list.

- [ ] **Step 1: Failing tests** — page test: editing a rule and saving sends one `PUT` with `version` and the full list; duplicate priority shows the API's 422 message inline; 409 keeps the draft; preview shows the deciding rule per table. Stories: default, empty list, preview loading, conflict.
- [ ] **Step 2–4:** RED, implement following the design system and `frontend/CLAUDE.md`, all frontend checks GREEN.
- [ ] **Step 5: Commit** `feat(console): edit discovery rules with a preview`

### Task 12: Console — Policies page and editor

**Files:**
- Create: `pages/PoliciesPage.tsx`, `components/PolicyEditor.tsx`, `components/OperationPolicySection.tsx` (+ tests, stories); route `/policies` and nav link "Policies" in `AppRoutes.tsx` and `components/AppShell.tsx` (+ tests)

**Interfaces:**
- Behaviour: list with name, description, version, attachment targets (an orphaned one marked "No longer in the catalog"), "Default" tag on `default`; create, edit (sends the read `version`), delete (disabled with a reason for `default` or attached policies). The editor shows top-level interval and dry run, then one section per operation with its enabled switch, scope (rewrite data files only), a "Trigger" group (cooldown, each condition as an optional threshold field, joined by the word "or") and an "Execution" group.

- [ ] **Step 1: Failing tests** — create sends the full content; edit sends `version`; the trigger group lists conditions separated by "or"; delete of `default` is disabled. Stories: list, editor, conflict, phone width.
- [ ] **Step 2–4:** RED, implement, frontend checks GREEN.
- [ ] **Step 5: Commit** `feat(console): maintenance policies page`

### Task 13: Console — applicable policy on catalog, namespace and table pages

**Files:**
- Create: `components/ApplicablePolicyPanel.tsx`, `components/AttachPolicyDialog.tsx` (+ tests, stories)
- Modify: `pages/CatalogPage.tsx`, `pages/NamespacePage.tsx`, `pages/TablePage.tsx`, `components/tabs/ReconciliationsTab.tsx`, `components/tabs/reconciliationText.ts` (+ tests, stories)

**Interfaces:**
- Behaviour: the panel shows the applicable policy, its version, and "Attached here" or "Inherited from namespace `prod.sales`" / "Platform default"; actions attach (choose a policy), replace, and detach (only when attached here). Each reconciliation row names "`policy` v3" linking to that version (read-only view fetched with the versions endpoint).

- [ ] **Step 1: Failing tests** — inherited text names the origin target; detach hidden when inherited; reconciliation row renders policy and version. Stories for each page state.
- [ ] **Step 2–4:** RED, implement, frontend checks GREEN.
- [ ] **Step 5: Commit** `feat(console): show and attach the applicable policy`

### Task 14: Cluster rebuild and verification

- [ ] **Step 1:** Build and deploy backend and console images (`minikube-deploy` skill, `KUBE_CONTEXT=retail-lakehouse`).
- [ ] **Step 2:** `task offboard KUBE_CONTEXT=retail-lakehouse`, `limactl disk delete colima-<profile>`, `task onboard KUBE_CONTEXT=retail-lakehouse`, `task apps:validate KUBE_CONTEXT=retail-lakehouse`, then `platform/25-lakehouse-control-plane/e2e.sh`.
- [ ] **Step 3:** Manual checks through the gateway on 8591: save a rule that excludes a managed table → it becomes unmanaged and its workflow ends after any run; attach a policy to a namespace → its tables' next reconciliation names it; open an old version from a reconciliation row.
- [ ] **Step 4:** Add a line to `docs/agents/project-history.md`; commit `docs(agents): record maintenance policies and discovery rules`.
