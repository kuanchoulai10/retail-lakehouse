# Backend Architecture Conformance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-lay out `src/table-maintenance/backend` on one aggregate axis, with `adapter/{inbound,outbound,hybrid}` and no infrastructure terms in `application/`, and enforce every rule with architecture tests.

**Architecture:** The aggregates are renamed and moved one at a time, and each commit stays green. Then the shared modules and the Temporal adapter are moved. Then the import boundary is introduced, with re-exports, a codemod and an AST test. After that import-linter is rewritten with no exemptions. The tests for each rule land in the task that makes the rule true.

**Tech Stack:** Python 3.14, uv, pytest, ty, ruff, import-linter, FastAPI, SQLAlchemy, temporalio 1.34, Helm (wave 25).

**Spec:** `docs/superpowers/specs/2026-10-29-backend-architecture-conformance-design.md`

## Global Constraints

- `B` = `src/table-maintenance/backend`. CHECKS (run from repo root, all must pass before every commit):
  - `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -q`
  - `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check`
  - `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`
  - `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
- No behaviour change except the one named in Task 6 (signal-with-start decided by `is_enrolled`).
- Aggregate set: `table`, `table_maintenance_run`, `table_maintenance_preset`, `table_discovery_rule`, `table_discovery_settings`. `shared` is the only extra name.
- Renames:
  - `ManagedTable` → `Table`; `MaintenanceRun` → `TableMaintenanceRun`; `PolicyTemplate` → `TableMaintenancePreset`; `DiscoveryRule` → `TableDiscoveryRule`; `DiscoverySettings` → `TableDiscoverySettings`.
  - Fields: `template_id` → `preset_id`; `source_template_id` → `source_preset_id`; `workflow_id` → `execution_ref`; `spark_application` → `job_name`; `needs_reconcile_workflow` → `is_enrolled`.
- Derived names follow the aggregate prefix. Examples: `TableId`, `TablesRepo`, `include_table`, `TableMaintenancePresetsRepo`, `create_table_maintenance_preset`.
- The catalog's Iceberg table read model is `TableMetadata`. It is never named `Table`.
- Existing CLAUDE.md rules still hold: one object per file, filename = primary export, `from __future__ import annotations`, ABC over Protocol, StrEnum, the port prefix rule and the DTO suffix rule.
- Shell rules:
  - no `cd`;
  - `uv run`, not bare python;
  - kubectl: verb first, flags last, no redirection after `--context`;
  - pass `KUBE_CONTEXT=retail-lakehouse` explicitly.
- YAML files get no explanatory comments.
- Commits:
  - conventional, ≤100-char lines, on `main`;
  - no push;
  - no attribution trailer.
- Moves use `git mv` so history follows the files. Every test file mirrors its source path under `tests/`.
- Never print secret values. Storage wipe is approved only for `table-maintenance-db` (Task 11).

## Review Focus

1. **Circular imports after re-exports.** Importing any boundary package in a fresh interpreter succeeds. Task 8 adds `test_every_boundary_imports_in_isolation`, which runs one subprocess per boundary.
2. **Temporal sandbox.** Workflows that import domain types through `application.port.*` re-exports still pass the sandbox. Port `__init__` files must not pull in I/O modules. The Temporal workflow tests in Task 6 and Task 9 run with the real sandbox; keep `test_temporal_workflow_determinism` green.
3. **The DB-wipe redeploy.** Three things must hold:
   - the chart's wait query uses the new table name `table_maintenance_presets`;
   - migrate seeds the `default` preset;
   - api / worker / event-consumer become Ready.

   Task 11 asserts all three in `validate.sh`.
4. **Stale Temporal state.** Workflows started by the old code would hit a renamed payload. Task 11 terminates them before the new worker rolls out, and checks that the admission workflow and the schedules come back.
5. **The `e2e.sh` jq paths.** They read the renamed JSON fields (`preset_id`, `execution_ref`) and the new routes. Task 11 runs `e2e.sh` end to end.

---

### Task 1: TableMaintenancePreset (was PolicyTemplate)

**Files:**
- Move: `$B/application/domain/model/policy_template/` → `$B/application/domain/model/table_maintenance_preset/`. Do the same for `port/inbound`, `port/outbound`, `service`, `adapter/inbound/web`, `adapter/outbound` and the matching `tests/` dirs.
- Modify:
  - every module that names `PolicyTemplate*`, `template_id` or `source_template_id`, including `TableDiscoveryRule` / `ManagedTable` fields, their row mappers, DTOs and the SQL columns;
  - `$B/bootstrap/migrate.py` (seed);
  - `$B/bootstrap/container/*`.

**Interfaces:**
- Produces:
  - aggregate `TableMaintenancePreset` / `TableMaintenancePresetId`;
  - repo port `TableMaintenancePresetsRepo`;
  - use cases `{Create,Get,List,Update,Delete}TableMaintenancePresetUseCase` with `…UseCaseInput` / `…UseCaseOutput`;
  - SQL table `table_maintenance_presets`;
  - API prefix `/v1/table-maintenance-presets`, tag `table-maintenance-presets`;
  - JSON field `preset_id` on discovery rules and `source_preset_id` on tables.

- [ ] **Step 1:** Update the web tests for presets. They must call `/v1/table-maintenance-presets`, assert `preset_id` / `source_preset_id` in the rule and table responses, and assert the old prefix returns 404.
- [ ] **Step 2:** Run them. Expected: FAIL (404 on the new path).
- [ ] **Step 3:** `git mv` the dirs. Rename the classes, files, fields, SQL table and columns, the router prefix and the `WebUseCases` field names, plus the migrate seed (`default` preset). The test files move and rename the same way.
- [ ] **Step 4:** Run CHECKS. Expected: all pass. `grep -rniE "policy.?template|template_id" $B --include='*.py'` returns nothing.
- [ ] **Step 5:** Commit `refactor(table-maintenance): rename PolicyTemplate to TableMaintenancePreset`.

### Task 2: Table (was ManagedTable), catalog read becomes TableMetadata

**Files:**
- Move `managed_table/` → `table/` in domain model, port inbound / outbound, service, web, adapter outbound and tests.
- Move `application/port/outbound/catalog/read_catalog/` → `application/port/outbound/table/read_table_metadata/`.
- Move `adapter/outbound/catalog/pyiceberg/` → `adapter/outbound/table/pyiceberg/`.
- Move `application/service/catalog/table_observation_from_gateway.py` → `application/service/table/`.
- Move the table-writing discovery services from `application/service/discovery/` → `application/service/table/`, with their inbound ports from `port/inbound/discovery/` → `port/inbound/table/`:
  - `process_table_hint`, `register_discovered_table`, `registration_outcome`, `sync_discovered_tables`, `table_hint_action`.

**Interfaces:**
- Produces:
  - aggregate `Table` / `TableId`, with `TableStatus` unchanged;
  - repo port `TablesRepo`;
  - use cases `IncludeTable`, `ExcludeTable`, `GetTable`, `ListTables`, `PauseTable`, `ResumeTable`, `ResetTableSelection`, `TriggerTableMaintenance`, `UpdateTableSettings`, `ProcessTableHint`, `SyncDiscoveredTables` (each with `…UseCase` / `…UseCaseInput` / `…UseCaseOutput`);
  - outbound `ReadTableMetadataGateway` with `ReadTableMetadataGatewayInput` / `…Output`. The old `ReadCatalogGatewayTable` / `…TableRef` / `…Observation` / `…ListInput` become `TableMetadata`, `TableMetadataRef`, `TableMetadataObservation`, `ReadTableMetadataGatewayListInput`, kept primitive-only;
  - adapter `ReadTableMetadataPyIcebergGateway`;
  - SQL table `tables`.
  - API paths under `/v1/tables` are unchanged. The `trigger` route keeps its path.

- [ ] **Step 1:** Rename the table web tests and the use-case tests to the new class names. Add `test_tables_sql_table_name_is_tables`, which asserts that the SQLAlchemy table's `.name == "tables"`.
- [ ] **Step 2:** Run. Expected: FAIL on import (the modules do not exist).
- [ ] **Step 3:** Do the moves and renames. The table aggregate keeps `needs_reconcile_workflow` for now; Task 6 renames it.
- [ ] **Step 4:** Run CHECKS. Expected: pass. `grep -rniE "managed_?table|ManagedTable|read_catalog|ReadCatalog" $B --include='*.py'` returns nothing.
- [ ] **Step 5:** Commit `refactor(table-maintenance): rename ManagedTable to Table and catalog reads to TableMetadata`.

### Task 3: TableDiscoveryRule and TableDiscoverySettings

**Files:**
- Move `discovery_rule/` → `table_discovery_rule/` and `discovery/` → `table_discovery_settings/` in domain model, port inbound / outbound, service, web, adapter outbound and tests.
- Move `domain/service/match_discovery_rule.py` → `domain/service/table_discovery_rule/match_table_discovery_rule.py`.

**Interfaces:**
- Produces:
  - aggregates `TableDiscoveryRule` / `TableDiscoveryRuleId` (with `RuleEffect` unchanged) and `TableDiscoverySettings` / `TableDiscoverySettingsId`;
  - repos `TableDiscoveryRulesRepo` and `TableDiscoverySettingsRepo`;
  - use cases `{Create,Delete,List,Update}TableDiscoveryRule` and `{Get,Update}TableDiscoverySettings`;
  - function `match_table_discovery_rule`;
  - outbound `UpdateTableDiscoveryScheduleGateway` under `port/outbound/table_discovery_settings/update_table_discovery_schedule/`;
  - SQL tables `table_discovery_rules` and `table_discovery_settings`;
  - API prefixes `/v1/table-discovery-rules` and `/v1/table-discovery-settings`; the old `/discovery` ad-hoc scan route moves under `/v1/table-discovery-settings`, same verb and sub-path.

- [ ] **Step 1:** Update the web tests to the new prefixes and assert the old prefixes return 404. Update the use-case tests to the new names.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Do the moves and renames.
- [ ] **Step 4:** Run CHECKS. Then grep:

  ```
  grep -rnE "\bDiscoveryRule\b|\bDiscoverySettings\b|discovery_rules_table|/discovery-rules|prefix=\"/discovery\"" $B --include='*.py'
  ```

  Expected: nothing.
- [ ] **Step 5:** Commit `refactor(table-maintenance): rename discovery rule and settings with the table prefix`.

### Task 4: TableMaintenanceRun, dissolve reconcile/ and spark/

**Files:**
- Move `maintenance_run/` → `table_maintenance_run/` in domain model, port inbound / outbound, service, web, adapter outbound and tests.
- Dissolve `port/inbound/reconcile/` and `service/reconcile/`:
  - `plan_table_maintenance` → `table/`;
  - `submit_maintenance_operation`, `delete_maintenance_job`, `get_maintenance_job_status`, `maintenance_procedure_args` → `table_maintenance_run/`.
- Move `port/outbound/spark/{submit,read,delete}_maintenance_job/` → `port/outbound/table_maintenance_run/`.
- Move `adapter/outbound/spark/k8s/` → `adapter/outbound/table_maintenance_run/k8s/`.
- Move `domain/service/spark_application_name.py` → `adapter/outbound/table_maintenance_run/k8s/spark_application_name.py`.

**Interfaces:**
- Produces:
  - aggregate `TableMaintenanceRun` / `TableMaintenanceRunId`. Its field `execution_ref: str` replaces `workflow_id`, with the same non-empty invariant. `OperationRun.job_name: str | None` replaces `spark_application`.
  - repo `TableMaintenanceRunsRepo`;
  - use cases `{Create,Get,List}TableMaintenanceRun(s)`, `ProcessTableMaintenanceCallback`, `RecordTableMaintenanceOperationResult`;
  - the Spark job gateways keep their names (`SubmitMaintenanceJobGateway` etc.), now under `table_maintenance_run/`. The k8s adapter computes the Spark application name and returns it as the job name.
  - `SendMaintenanceResultGatewayInput.execution_ref` replaces `workflow_id`;
  - SQL table `table_maintenance_runs`, column `execution_ref`;
  - API:
    - `GET /v1/table-maintenance-runs/{run_id}`;
    - `POST /v1/table-maintenance-runs/{run_id}/operations/{operation}/result` (the callback; the backend builds the callback URL, so the Spark runtime is unchanged);
    - `GET /v1/tables/{table_uuid}/table-maintenance-runs`;
    - the JSON field is `execution_ref`.

- [ ] **Step 1:** Update the web tests to the new routes and field, and assert the old routes return 404. Update the domain test for the `execution_ref` invariant. Update the k8s adapter test so it asserts that the submitted manifest's name equals `spark_application_name(run_id, op, attempt)` from its new location.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Do the moves and renames. The Temporal code that sets `workflow_id` now passes it as `execution_ref`.
- [ ] **Step 4:** Run CHECKS. `grep -rnE "service/reconcile|port/inbound/reconcile|outbound/spark|spark_application\b|\bworkflow_id\b" $B/application` returns nothing.
- [ ] **Step 5:** Commit `refactor(table-maintenance): rename MaintenanceRun and fold reconcile and spark into aggregates`.

### Task 5: Shared modules on the aggregate axis

**Files:**
- **Domain model to `shared/`:** move `domain/model/{maintenance,maintenance_settings}/` → `domain/model/shared/`. `workflow_ids.py` is not moved here; Task 6 owns it.
- **Observation:** move `domain/model/observation/` → `domain/model/table/` (only Table planning uses it). If another aggregate imports it, put it in `shared/` instead.
- **Domain services to `table/`:** move the remaining `domain/service/*.py` → `domain/service/table/`:
  - `build_partition_filters`, `compute_reducible_files`, `plan_manual_maintenance`, `plan_scheduled_maintenance`, `positive_int_property`, `resolve_target_file_size`.
  - A service used by several aggregates goes to `domain/service/shared/`.
- **Application services to `shared/`:** move `service/maintenance_settings/` and `service/translate_domain_errors.py` → `service/shared/`.
- **Outbound adapter:** move `adapter/outbound/sql/` → `adapter/outbound/shared/sql/`.
- Test: create `$B/tests/architecture/test_aggregate_axis.py`.

**Interfaces:**
- Produces: `AGGREGATES = {"table", "table_maintenance_run", "table_maintenance_preset", "table_discovery_rule", "table_discovery_settings"}` in `$B/tests/architecture/aggregates.py`, for reuse by later tests.

- [ ] **Step 1: Write the failing test** in `test_aggregate_axis.py`:
  - `test_layer_subdirs_are_aggregates` is parametrized over these layer dirs:
    - `application/domain/model`, `application/domain/service`;
    - `application/port/inbound`, `application/port/outbound`;
    - `application/service`;
    - `adapter/inbound/web`, `adapter/outbound`.

    It asserts `subdirs(layer) <= AGGREGATES | {"shared"}`.
  - `test_inbound_ports_match_services`: `subdirs("application/port/inbound") == subdirs("application/service") - {"shared"}`, and `"shared" not in subdirs("application/port/inbound")`.
  - `test_no_modules_at_layer_root`: every layer dir's `.py` files == `{"__init__.py"}`.
  - `subdirs` ignores `__pycache__`.
- [ ] **Step 2:** Run `pytest tests/architecture/test_aggregate_axis.py -v`. Expected: FAIL. The listed `maintenance`, `observation` and `sql` dirs and root modules are reported.
- [ ] **Step 3:** Do the moves. `adapter/hybrid/temporal/outbound` joins the parametrization in Task 6.
- [ ] **Step 4:** Run CHECKS. Expected: pass.
- [ ] **Step 5:** Commit `refactor(table-maintenance): put shared modules on the aggregate axis`.

### Task 6: Temporal as a hybrid adapter, intention ports, no infrastructure terms in application

**Files:**
- **Inbound Temporal code:** move `adapter/inbound/temporal/{workflows,activities}/` and `adapter/inbound/temporal/ensure_*.py` → `adapter/hybrid/temporal/inbound/`.
- **Contracts:** move `adapter/temporal_contracts/*` → `adapter/hybrid/temporal/contracts/`. Also move `application/domain/model/maintenance/workflow_ids.py` → `adapter/hybrid/temporal/contracts/workflow_ids.py` (it was moved to `shared/` in Task 5).
- **Outbound Temporal code:** move these into `adapter/hybrid/temporal/outbound/<aggregate>/`:
  - `adapter/outbound/workflow/temporal/*`
  - `adapter/outbound/table_discovery_settings/temporal/*`
  - `adapter/outbound/temporal/async_loop_bridge.py`, which goes to `adapter/hybrid/temporal/outbound/shared/`.
- **Replace the table signal port:** `application/port/outbound/workflow/send_table_signal/` → `application/port/outbound/table/send_table_change/`.
- **The other two workflow ports:**
  - `application/port/outbound/workflow/send_maintenance_result/` → `application/port/outbound/table_maintenance_run/send_maintenance_result/`.
  - `application/port/outbound/workflow/send_discovery_request/` → `application/port/outbound/<aggregate of its caller>/send_discovery_request/`. Today `process_table_hint` is the only service that calls it, so `table/`.
- Create: `application/domain/model/table/table_change.py`.
- Test: create `$B/tests/architecture/test_adapter_layout.py` and `$B/tests/architecture/test_no_infrastructure_terms.py`.

**Interfaces:**
- Produces:
  - `class TableChange(StrEnum)`: `UPDATED = "updated"`, `SETTINGS_CHANGED = "settings_changed"`, `PAUSED = "paused"`, `RESUMED = "resumed"`, `STOPPED = "stopped"`, `MAINTENANCE_REQUESTED = "maintenance_requested"`.
  - `SendTableChangeGateway.send(input: SendTableChangeGatewayInput) -> None`, where:

    ```python
    @dataclass(frozen=True)
    class SendTableChangeGatewayInput:
        table_uuid: str
        table_name: str
        change: str            # a TableChange value
        is_enrolled: bool
        operations: list[str] = field(default_factory=list)  # only for maintenance_requested
    ```
  - `SendTableChangeTemporalGateway`. It maps `change` to the signal:

    | change | signal |
    |---|---|
    | `updated` | `SIGNAL_TABLE_UPDATED` |
    | `settings_changed` | `SIGNAL_SETTINGS_CHANGED` |
    | `paused` | `SIGNAL_PAUSE` |
    | `resumed` | `SIGNAL_RESUME` |
    | `stopped` | `SIGNAL_STOP` |
    | `maintenance_requested` | `SIGNAL_TRIGGER_NOW`, with payload `{"operations": operations}` |

    It uses signal-with-start exactly when `is_enrolled` is true. This is the one behaviour change: `pause` of an enrolled table with no running workflow now starts it paused, which is consistent with the earlier R38 / fix-wave intent.
  - `Table.is_enrolled` (ACTIVE or PAUSED) replaces `needs_reconcile_workflow`.

- [ ] **Step 1: Write the failing tests**
  - `test_adapter_layout.py`:
    - `test_adapter_top_level`: `subdirs("adapter") == {"inbound", "outbound", "hybrid"}`.
    - `test_hybrid_tech_has_both_directions`: for every `t` in `subdirs("adapter/hybrid")`, `subdirs(f"adapter/hybrid/{t}") == {"inbound", "outbound", "contracts"}`.
    - Add `adapter/hybrid/temporal/outbound` to `test_layer_subdirs_are_aggregates`.
  - `test_no_infrastructure_terms.py`:
    - `BANNED = {"temporal", "workflow", "signal", "activity", "spark", "k8s", "kubernetes", "sql", "pyiceberg", "iceberg_rest", "kafka", "polaris"}`.
    - Walk `application/**/*.py`. Tokenize these names, split on `_` and camelCase, lower-cased:
      - every path segment;
      - every class, function and argument name;
      - every attribute and dataclass field name;
      - every assigned module-level name.
    - Assert that no token is in `BANNED`. Docstrings, comments and string literals are not scanned.
    - The failure message lists `file:line name`.
    - Add `test_banned_term_detector_catches_camel_and_snake`, a unit test of the tokenizer on `needsReconcileWorkflow`, `spark_application` and `SIGNAL_STOP`.
  - Update the gateway-adapter tests to the new port, with the change→signal table above and the `is_enrolled` → start rule, including the pause case.
- [ ] **Step 2:** Run the two new test files and the gateway test. Expected: FAIL. The layout test reports `temporal_contracts`. The terms test reports `workflow_ids`, `needs_reconcile_workflow`, `SendTableSignal…`, `SIGNAL_*`.
- [ ] **Step 3:** Do the moves. Replace every `SendTableSignalGatewayInput(signal=SIGNAL_*, …)` call in `application/service/**` with `SendTableChangeGatewayInput(change=TableChange.X.value, is_enrolled=table.is_enrolled, …)`. Rename the `signal_gateway` constructor parameters to `table_change_gateway`. Update `bootstrap/container` wiring and the worker / API imports.
- [ ] **Step 4:** Run CHECKS. Update the `.importlinter` contracts to the moved paths only; Task 9 rewrites them. Expected: pass.
- [ ] **Step 5:** Commit `refactor(table-maintenance): make Temporal a hybrid adapter and speak intent in ports`.

### Task 7: Existing naming tests on the new layout

**Files:**
- Modify the five tests so they walk the new trees and keep all their current assertions (port prefix = PascalCase dir name, DTO suffixes, primitive-only gateway I/O, service structure):
  - `$B/tests/architecture/test_directory_structure.py`
  - `test_inbound_port_structure.py`
  - `test_outbound_port_structure.py`
  - `test_dto_naming.py`
  - `test_service_structure.py`

- [ ] **Step 1:** Make each test fail on a planted violation. Add a temporary `application/port/outbound/table/send_bad/input.py` that imports `application.domain`, and check that `test_outbound_port_structure` FAILS on it. Then delete the planted file. Do the same for one inbound-port and one DTO case. The point is to prove that the walkers still reach the moved dirs.
- [ ] **Step 2:** Fix any walker that silently skips the new paths, for example a hard-coded `managed_table` / `reconcile` list or a top-level `adapter/inbound/temporal`. Hard-coded aggregate lists are replaced with `AGGREGATES`.
- [ ] **Step 3:** Run CHECKS. Expected: pass.
- [ ] **Step 4:** Commit `test(table-maintenance): point naming architecture tests at the new layout`.

### Task 8: Import boundary and re-exports

**Files:**
- Create:
  - `$B/tests/architecture/boundaries.py`
  - `$B/tests/architecture/test_import_boundary.py`
  - `$B/scripts/rewrite_boundary_imports.py`, a one-off codemod. It is deleted at the end of this task, so it is not committed.
- Modify: every boundary `__init__.py` and every import that crosses a boundary in `application/`, `adapter/`, `bootstrap/`, `base/`, `entrypoint.py` and `tests/`.

**Interfaces:**
- Produces `def boundaries() -> set[str]` (dotted package names), derived from the directory rules:
  - `application.{domain.model,domain.service,port.inbound,port.outbound,service}.<agg>`
  - `adapter.inbound.web.<agg>`, `adapter.inbound.web` (root modules only), `adapter.inbound.event_consumer` and its child packages
  - `adapter.outbound.<agg>.<tech>`
  - `adapter.hybrid.<t>.{inbound,outbound,contracts}` and their child packages
  - `base`, `application.exceptions`, `bootstrap.configs`, `bootstrap.container`

  A module belongs to the innermost boundary containing it. Boundaries do not nest for re-export purposes. Rule for child packages: under `hybrid/<t>/inbound`, `workflows/` and `activities/` are each a boundary. Under `hybrid/<t>/outbound`, each `<agg>/` is a boundary.

- [ ] **Step 1: Write the failing tests** in `test_import_boundary.py`:
  - `test_no_import_past_a_boundary`:
    - AST-walk every `.py` under `application`, `adapter`, `base`, `bootstrap` and `tests`, plus `entrypoint.py`.
    - For each `from X import …` / `import X` where `X` is project-internal, let `b = innermost_boundary(X)` and let `own` be the importing module's boundary. If `b != own`, then `X` must equal `b`.
    - Relative imports are disallowed.
    - The failure lists `file:line X → expected b`.
  - `test_boundary_all_is_complete`: for each boundary `b`, `b.__init__` defines `__all__`. For each non-private module `m` directly in `b`, or in a non-boundary subpackage of `b` (for example a port's `include_table/` folder), the primary export of `m` is in `__all__`. The primary export is the public class or function whose snake_case name equals the module name, or for a constants module its public names.
  - `test_every_boundary_imports_in_isolation`: parametrized over `boundaries()`. It runs `subprocess.run([sys.executable, "-c", f"import {b}"], cwd=B)` and asserts returncode 0. This covers Review Focus 1.
- [ ] **Step 2:** Run. Expected: FAIL with hundreds of deep imports listed, and missing `__all__` entries.
- [ ] **Step 3:** Fill every boundary `__init__.py`. A port boundary's `__init__` also re-exports the domain types that appear in its signatures; for example, `application.port.outbound.table` exports `Table` and `TableId`. This prepares Task 9. Then run the codemod, which rewrites each crossing import to `from <boundary> import Name` and merges duplicates. Run `ruff check --fix .` and `ruff format .`.
- [ ] **Step 4:** Run CHECKS. Expected: pass. Delete the codemod.
- [ ] **Step 5:** Commit `refactor(table-maintenance): import only through package boundaries and test it`.

### Task 9: import-linter without exemptions

**Files:**
- Modify: `$B/.importlinter`, with a full rewrite.
- Modify: the adapter modules that still import `application.domain` / `application.service`, so that they import the same names from the port boundary.
- Create: `$B/tests/architecture/test_importlinter_config.py`.

**Interfaces:**
- Contracts (names verbatim):
  - `domain-pure` (forbidden):
    - source `application.domain`;
    - forbidden:
      - `application.port`, `application.service`, `application.exceptions`;
      - `adapter`, `bootstrap`;
      - `temporalio`, `pyiceberg`, `pyarrow`, `sqlalchemy`, `fastapi`, `kubernetes`, `confluent_kafka`, `pydantic`.
  - `application-ring-order` (layers): `application.service` → `application.port` → `application.domain.service` → `application.domain.model`.
  - `application-no-outer-rings` (forbidden):
    - source `application`;
    - forbidden: `adapter`, `bootstrap`, plus the same frameworks.
  - `adapters-see-only-ports` (forbidden):
    - source `adapter`;
    - forbidden `application.domain`, `application.service`;
    - `allow_indirect_imports = true`.
  - `adapter-directions-separate` (independence): `adapter.inbound`, `adapter.outbound`, `adapter.hybrid`.
  - `hybrid-directions-separate` (independence): `adapter.hybrid.temporal.inbound`, `adapter.hybrid.temporal.outbound`.
  - `hybrid-contracts-neutral` (forbidden):
    - source `adapter.hybrid.temporal.contracts`;
    - forbidden: `application.domain`, `application.service`, `adapter.inbound`, `adapter.outbound`, `adapter.hybrid.temporal.inbound`, `adapter.hybrid.temporal.outbound`, `bootstrap`, plus the frameworks.
  - `hybrid-contracts-private` (forbidden):
    - source: `adapter.inbound`, `adapter.outbound`, `application`;
    - forbidden: `adapter.hybrid.temporal.contracts`.
  - `temporal-workflows-sandbox-safe` (forbidden):
    - source `adapter.hybrid.temporal.inbound.workflows`;
    - forbidden:
      - `adapter.hybrid.temporal.inbound.activities`;
      - `adapter.inbound`, `adapter.outbound`, `bootstrap`;
      - the frameworks except `temporalio`;
      - every `application.port.*.<agg>` boundary whose `__init__` imports an I/O module.

      Keep the spirit of the existing contract and list the boundaries explicitly.
  - `inbound-channels-independent` (independence): `adapter.inbound.web`, `adapter.inbound.event_consumer`, `adapter.hybrid.temporal.inbound`.
  - `adapters-no-bootstrap`, `configs-leaf`, `base-isolation`: keep them as today, with the new paths.
  - The old `temporal-contracts-neutral` and its `ignore_imports` are removed.
- Tests in `test_importlinter_config.py`:
  - `test_no_ignore_imports`: parse the file with `configparser` and assert that no section has `ignore_imports`.
  - `test_required_contracts_present`: the contract ids above ⊆ the sections.

- [ ] **Step 1:** Write `test_importlinter_config.py`. Run it. Expected: FAIL (`ignore_imports` present; new ids missing).
- [ ] **Step 2:** Rewrite `.importlinter`. Run `lint-imports`. Expected: FAIL, listing the adapter → domain imports (about 20 files).
- [ ] **Step 3:** Change those imports to the port boundaries. Add any missing domain re-export to the port `__init__` that uses the type. If a type an adapter needs belongs to no port signature, it means the port is incomplete: add the type to the port that the adapter implements or calls. Do not import the domain.
- [ ] **Step 4:** Run CHECKS. Expected: pass.
- [ ] **Step 5:** Commit `refactor(table-maintenance): enforce ring and adapter contracts without exemptions`.

### Task 10: Docs

**Files:**
- Modify:
  - `CLAUDE.md`: the Backend Structure tree, Rules, the naming tables and Project Status (a 2026-10-29 line);
  - `docs/adr/0001-table-identity-by-iceberg-uuid.md`;
  - `docs/adr/0002-entity-workflow-per-table.md`;
  - `docs/iceberg/table-maintenance.md`;
  - `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md`: a short note that ports are grouped by aggregate.

- [ ] **Step 1:** In the CLAUDE.md Backend Structure section:
  - show the new tree: `adapter/{inbound,outbound,hybrid}`, the aggregate dirs and `shared`;
  - list each rule with the test or contract that enforces it, for example "aggregate axis — `tests/architecture/test_aggregate_axis.py`";
  - replace the stale `scheduler` / `messaging` / `jobs` text with the current components (`api`, `worker`, `event-consumer`, `migrate`).
- [ ] **Step 2:** Replace the old terms in the ADRs and docs. Check with:

  ```
  grep -rniE "managed.?table|policy.?template|discovery.rule|maintenance_run\b" CLAUDE.md docs/adr docs/iceberg/table-maintenance.md
  ```

  Expected: only historical mentions that say "formerly".
- [ ] **Step 3:** Commit `docs(table-maintenance): describe the conformed backend layout and its enforcing tests`.

### Task 11: Deploy, wipe the DB, reset Temporal, e2e

**Files:**
- Modify:
  - `platform/25-lakehouse-control-plane/chart/templates/_helpers.tpl`: the wait query uses `table_maintenance_presets`;
  - any template, `values.yaml`, `bootstrap.sh`, `validate.sh`, `e2e.sh` or `README.md` that uses the old routes, fields or table names (`/v1/policy-templates`, `/v1/discovery-rules`, `/v1/discovery`, `/v1/runs`, `template_id`, `workflow_id`, `policy_templates`).

- [ ] **Step 1:** Update the scripts and the chart. In `validate.sh`, assert:
  - `GET /v1/table-maintenance-presets` lists `default`;
  - `GET /v1/table-discovery-settings` and `GET /v1/tables` return 200;
  - the old `/v1/policy-templates` returns 404.

  Run `helm lint` and `helm template` clean.
- [ ] **Step 2:** Run `platform/25-lakehouse-control-plane/build.sh` with `KUBE_CONTEXT=retail-lakehouse`.
- [ ] **Step 3: Reset state.**
  - Scale `api`, `worker` and `event-consumer` to 0.
  - Wipe `table-maintenance-db`: drop and recreate the `public` schema with `psql` in the db pod. This is approved; never print the password.
  - In the Temporal admin-tools pod:
    - `temporal workflow terminate --query 'WorkflowType STARTS_WITH "Table"' --reason "backend relayout" --yes`
    - delete every `table-discovery:catalog=*` schedule.
- [ ] **Step 4:** Run `platform/25-lakehouse-control-plane/bootstrap.sh` and `validate.sh` with `KUBE_CONTEXT=retail-lakehouse`. Then run `task apps:validate KUBE_CONTEXT=retail-lakehouse`. Expected: exit 0. In Temporal, `table-maintenance-admission` is Running and the `table-discovery:catalog=iceberg` schedule exists.
- [ ] **Step 5:** Run `platform/25-lakehouse-control-plane/e2e.sh` with `KUBE_CONTEXT=retail-lakehouse`. Expected: every operation SUCCEEDED, including the `o'neil` partition. The e2e recreates its preset and include rule against the new routes.
- [ ] **Step 6:** Commit `fix(lakehouse-control-plane): follow the renamed API, fields and tables`.
