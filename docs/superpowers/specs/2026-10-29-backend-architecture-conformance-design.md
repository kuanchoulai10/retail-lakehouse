# Table Maintenance backend: architecture conformance

## Intent

The `src/table-maintenance/backend` code should read the way the owner pictures DDD, Ports & Adapters and Clean Architecture. This is not a one-off cleanup. Every rule below becomes an architecture test, so the codebase cannot drift back.

Problems seen today:
- **A third adapter direction.** `adapter/temporal_contracts/` sits beside `inbound/` and `outbound/`.
- **Infrastructure terms in the core.** Temporal and Spark concepts live in the domain and application layers:
  - `workflow_ids.py` holds the task queue, the signal names and the workflow ids;
  - the `needs_reconcile_workflow` property;
  - the `workflow_id` and `spark_application` fields;
  - the `spark_application_name` domain service;
  - services pass Temporal signal names through a port.
- **Adapters reach past application into the domain.** 20 adapter files import `application.domain` directly. The import-linter `layers` contract does not stop skip-layer imports, and an `ignore_imports` entry opens a back door.
- **Many classification axes.** Ports, services, adapters and domain modules are grouped by different things: by aggregate (`managed_table`), by process (`reconcile`, `discovery`), by external system (`catalog`, `spark`, `workflow`) and by technology (`sql/`, `temporal/`).
- **Deep imports.** About 1,100 import lines reach 4 or more segments deep.
- **Names the owner dislikes.** `PolicyTemplate`, `ManagedTable` and `DiscoveryRule`.

The project is in development. API paths, DB table names and data may change freely; there are no external users and no migration story to keep.

## Goals

1. One classification axis everywhere: the aggregate.
2. `adapter/` holds only `inbound/`, `outbound/` and `hybrid/`.
3. No infrastructure concept in `application/`, which covers the domain, the ports and the services.
4. Adapters depend on `application.port.*` only, never on `application.domain` or `application.service`.
5. Each aggregate package re-exports its public API, and nobody imports past a boundary.
6. The new names apply in code, the REST API, the DB, the Helm chart, the scripts and the docs.
7. Every rule above is enforced by a test that fails when it is broken.

## Non-goals

- No behaviour change. The workflows, the planning logic, the retries and the API semantics stay as they are; only names and locations change.
- No new features. The known follow-ups in CLAUDE.md stay open.
- No change to the Spark runtime (`src/table-maintenance/runtime/spark`), except where a callback wire field is renamed.
- No Alembic and no data migration.

## Anti-goals

- A rule written only in docs or CLAUDE.md, with no test behind it.
- Allow-lists or `ignore_imports` that quietly exempt files from a rule.
- Moving the Temporal pollution from the adapter into `application/`. For example, a "workflow port" that still speaks of signals.

## Decisions

### Names (owner's decisions)

| Old | New | Package dir |
|---|---|---|
| `ManagedTable` | `Table` | `table/` |
| `MaintenanceRun` | `TableMaintenanceRun` | `table_maintenance_run/` |
| `PolicyTemplate` | `TableMaintenancePreset` | `table_maintenance_preset/` |
| `DiscoveryRule` | `TableDiscoveryRule` | `table_discovery_rule/` |
| `DiscoverySettings` | `TableDiscoverySettings` | `table_discovery_settings/` |

Derived names follow the same pattern:
- types: `TableId`, `TableMaintenancePresetId`, `TablesRepo`, `TableMaintenanceRunsRepo`;
- use cases: `include_table`, `pause_table`, `update_table_settings`, `create_table_maintenance_preset`;
- fields: `template_id` → `preset_id`, `source_template_id` → `source_preset_id`.

The Iceberg table read from the catalog is a separate concept. Name it `TableMetadata` (or similar) so it does not collide with the `Table` aggregate.

Semantics to keep in mind for the preset: a preset's settings are copied onto a table when the table is enrolled. Editing the preset later does not change tables that already used it. `source_preset_id` only records where the settings came from.

### One axis: the aggregate

The aggregate set is `table`, `table_maintenance_run`, `table_maintenance_preset`, `table_discovery_rule`, `table_discovery_settings`, plus `shared` for things used by several aggregates. In each of these directories, the first-level subdirectories come from that set:

- `application/domain/model/`
- `application/domain/service/`
- `application/port/inbound/`
- `application/port/outbound/`
- `application/service/`
- `adapter/inbound/web/`
- `adapter/outbound/`
- `adapter/hybrid/temporal/outbound/`

`port/inbound/` and `service/` must have the same set, with one exception: `service/` may also have `shared/` for helpers that are not use cases. These are `translate_domain_errors`, the settings dict codecs and `table_observation_from_gateway`. An empty `port/inbound/shared/` is not created. The other directories may use a subset. (Builder-check call.)

No directory may be named after a process or an external system, such as `reconcile/`, `discovery/`, `catalog/`, `spark/` or `workflow/`.

Placement rules:
- **Use case.** It goes under the aggregate it writes. A read-only use case goes under the aggregate it reads. For example:
  - `process_table_hint` and `sync_discovered_tables` write `Table`, so they go under `table/`;
  - `plan_table_maintenance` goes under `table/`;
  - `submit_maintenance_operation`, `delete_maintenance_job` and `get_maintenance_job_status` go under `table_maintenance_run/`.
- **Outbound port.** It goes under the aggregate whose use cases call it. For example:
  - catalog read → `table/read_table_metadata`;
  - Spark job submit / read / delete → `table_maintenance_run/`;
  - discovery schedule → `table_discovery_settings/`.

  A port called from several aggregates goes in `shared/`.
- **Domain module.** Value objects used by several aggregates (`MaintenanceSettings`, `MaintenanceOperation`, the maintenance plan) go in `domain/model/shared/`. A value object used by one aggregate lives in that aggregate.
- **Root-level files.** The only `.py` file allowed directly at the root of each layer directory above is `__init__.py`. Helpers such as `translate_domain_errors` go in `shared/`.

Outbound adapters are `adapter/outbound/<aggregate>/<tech>/`, for example `table/sql/`, `table/pyiceberg/` and `table_maintenance_run/k8s/`. Technology code shared across aggregates goes in `adapter/outbound/shared/<tech>/`: the SQL metadata, `create_schema` and the codecs.

### adapter/: inbound, outbound, hybrid

```
adapter/
├── inbound/{web, event_consumer}/
├── outbound/<aggregate>/<tech>/
└── hybrid/temporal/
    ├── inbound/     ← workflows, activities, ensure_* (schedule / admission bootstrapping)
    ├── outbound/    ← <aggregate>/ send_* gateways, schedule gateway, the async loop bridge
    └── contracts/   ← today's adapter/temporal_contracts + the moved workflow_ids
```

The owner's rules:
- `adapter/` contains only `inbound/`, `outbound/` and `hybrid/`.
- A technology goes under `hybrid/<tech>/` only if it has both `inbound/` and `outbound/` parts. Each `hybrid/<tech>/` holds exactly `inbound/`, `outbound/` and `contracts/`.
- `hybrid/<tech>/contracts` is imported only by `hybrid/<tech>/inbound`, `hybrid/<tech>/outbound`, `bootstrap` and `tests`.
  - `bootstrap` is allowed because it is the composition root, which may import every layer by the existing rule. It needs the task queue and the lease defaults.
  - `tests` is allowed because tests are not production code.
  - These two are rules of the contract itself, not `ignore_imports` entries. (Builder-check call.)
- `hybrid/<tech>/inbound` and `hybrid/<tech>/outbound` never import each other.
- `contracts` imports only stdlib and `application.port.*`.

### Removing infrastructure from application/

| Today | Target |
|---|---|
| `domain/model/maintenance/workflow_ids.py` (task queue, signal names, workflow / schedule ids) | `adapter/hybrid/temporal/contracts/` |
| `SendTableSignalGateway(signal=SIGNAL_*, start_if_missing=…)`, called by services with Temporal signal names | An intention port, e.g. `SendTableChangeGateway` with `change` ∈ resumed / paused / stopped / settings_changed / maintenance_requested / updated; the Temporal adapter maps each change to a signal and decides signal-with-start from whether the table is enrolled |
| `ManagedTable.needs_reconcile_workflow` (ACTIVE or PAUSED) | `Table.is_enrolled` (same truth table) |
| `MaintenanceRun.workflow_id` | `TableMaintenanceRun.execution_ref`: an opaque string supplied by whatever runs it; the API field is renamed the same way |
| `OperationRun.spark_application` | `job_name` |
| `domain/service/spark_application_name.py` | `adapter/outbound/table_maintenance_run/k8s/` |
| `send_discovery_request`, `send_maintenance_result` (`workflow/` ports) | Intention names under their aggregate; the Temporal word stays out of the port |

Workflows still use domain value objects for deterministic decisions, for example `MaintenanceOperation` and the attempt policy. They now import them through `application.port.*` re-exports, like every other adapter. The sandbox-safety contract (`temporal-workflows-sandbox-safe`) is kept and rewritten for the new paths.

### Adapters see only ports

- Each port package re-exports the domain types its signatures use. For example, `application.port.outbound.table` exports `TablesRepo` and `Table`.
- The SQL repos keep returning domain aggregates. This is the standard DDD repository; the owner chose this over primitive snapshot DTOs.
- Adapters may import:
  - `application.port.*`;
  - `application.exceptions`;
  - `base`;
  - their own `hybrid/<tech>/contracts`;
  - third-party libraries.

### Layer stack (builder-check call)

The rings, from outer to inner, are `bootstrap` → `adapter` → `application.port` → `application.domain`.

- **No-skip between rings.** `adapter` may not import `application.domain` or `application.service`. That rule is enforced by a `forbidden` contract with `allow_indirect_imports = true`.
  - The setting is not an exemption. The rule is about what an adapter names in its own imports, and reaching a domain type through a port re-export is exactly the intended path.
- **Inside the application ring.** `application.service` is part of the application ring. It may import `application.port` and `application.domain`, as the CLAUDE.md diagram already shows (`application ──> domain`). A `layers` contract keeps the direction inside the ring: `service` → `port` → `domain.service` → `domain.model`, with no upward imports.
- **Shared kernel.** `base` and `application.exceptions` are a shared kernel. Every ring may import them, and they import nothing from the project.
  - `application.exceptions` is the error vocabulary that the web adapter is already required to catch.

### Re-export and the import boundary

- A **boundary** is:
  - each aggregate-level package in the layer directories above;
  - each `adapter/outbound/<aggregate>/<tech>/`;
  - each `adapter/hybrid/<tech>/{inbound,outbound,contracts}`;
  - each `adapter/inbound/<channel>`;
  - `base`, `application.exceptions`, `bootstrap.configs`, `bootstrap.container`.

  The test derives the boundary list from these directory rules. There is no hand-kept list.
- **Boundaries do not nest.** A module belongs to the innermost boundary that contains it. For example:
  - `adapter.inbound.web` is a boundary only for the modules directly inside it, such as `create_app.py`.
  - `adapter.inbound.web.table` is its own boundary.
  - So `create_app.py` writes `from adapter.inbound.web.table import router`.

  A parent's `__all__` does not re-export its child boundaries. (Builder-check call.)
- Outside a boundary, code imports only `from <boundary> import Name`. This includes `tests/`.
- Inside a boundary, modules import each other directly, which avoids circular imports. This is the existing CLAUDE.md rule.
- Every boundary `__init__.py` defines `__all__`. `__all__` must contain the primary export of every non-private module below that boundary.

## Acceptance tests

All of these live in `tests/architecture/` (or `.importlinter`) and run in `pytest -v` / `lint-imports`.

1. **Adapter layout.**
   - `adapter/` has exactly the subdirectories `inbound`, `outbound`, `hybrid`.
   - Each `hybrid/<tech>` has exactly `inbound`, `outbound`, `contracts`.
2. **Aggregate axis.**
   - The first-level subdirectories of the layer directories come from the aggregate set plus `shared`.
   - `port/inbound` and `service` are equal sets.
   - No `.py` file except `__init__.py` sits at a layer root.
3. **No infrastructure terms in `application/`.** Module paths, class names, function names, attribute and field names, and string constants used as identifiers contain none of these words:
   - workflow engine: `temporal`, `workflow`, `signal`, `activity`;
   - runtime: `spark`, `k8s`, `kubernetes`;
   - data and messaging: `sql`, `pyiceberg`, `iceberg_rest`, `kafka`, `polaris`.

   The check is case-insensitive and token-based. Docstrings and comments are not checked.
4. **import-linter.**
   - **Adapters:** they never import `application.domain` or `application.service`.
   - **Layering:**
     - each layer imports only the layer directly below it (no-skip);
     - domain imports only `base` and stdlib;
     - services import ports and the domain;
     - ports import the domain.
   - **Hybrid adapters:** the hybrid contract rules apply.
   - **Inbound and outbound:** they stay separated.
   - **Bootstrap:** it is the only module that imports everything.
   - **Domain dependencies:** the domain forbids third-party framework imports. That covers `temporalio`, `pyiceberg`, `pyarrow`, `sqlalchemy`, `fastapi`, `kubernetes`, `confluent_kafka`, `pydantic`.
5. **No exemptions.** A test parses `.importlinter` and fails if any `ignore_imports` key exists.
6. **Import boundary.** An AST test fails on any import that reaches past a boundary from outside it, in source or tests. A second test checks every boundary's `__all__` for completeness.
7. **Existing naming tests.** `test_inbound_port_structure`, `test_outbound_port_structure`, `test_dto_naming`, `test_service_structure` and `test_directory_structure` are updated to the new layout and keep their current guarantees, such as the port class prefix matching the directory name and primitive-only gateway I/O.

Each new test is written first and seen failing against today's tree, then the code is moved until it passes.

## Outside the backend code

- **REST API.**
  - The prefixes become:
    - `/v1/tables` (unchanged);
    - `/v1/table-maintenance-presets`;
    - `/v1/table-discovery-rules`;
    - `/v1/table-discovery-settings`;
    - the maintenance-run routes, renamed to match `table_maintenance_run`.
  - JSON fields use the new names: `preset_id`, `source_preset_id`, `execution_ref`.
  - Tags match the prefixes.
- **DB.**
  - Tables are renamed after the aggregates: `tables`, `table_maintenance_runs`, `table_maintenance_presets`, `table_discovery_rules`, `table_discovery_settings`.
  - The owner approved wiping `table-maintenance-db` and recreating it from `migrate`. The migrate seed creates the `default` preset.
- **Temporal state (builder-check call).** Replay compatibility is not kept. During development the owner does not want to carry evolution cost. Activity and signal payloads, moved dataclasses and field renames may change freely.
  - Before the new worker starts, the redeploy terminates every workflow execution and deletes every schedule in the Temporal `default` namespace that belongs to table maintenance.
  - On start, the worker re-creates the schedules and the admission workflow.
  - The first discovery sync re-creates the per-table reconciliation workflows.
  - This also makes the admission workflow pick up the 22500 s lease.
- **Helm chart and wave 25.**
  - Rename anything that carries the old names in `chart/templates`, `bootstrap.sh`, `validate.sh`, `e2e.sh` and the README.
  - The Temporal workflow names and ids (2026-10-26 rename) do not change.
- **Spark runtime.** Change it only if a callback field name changes.
- **Docs.**
  - ADRs 0001 and 0002 and `docs/iceberg/table-maintenance.md` use the new terms.
  - The CLAUDE.md "Backend Structure" tree and rules describe the new layout and point to the tests that enforce it.
  - The CLAUDE.md naming tables and Project Status are updated.

## Done means

- `pytest -v`, `ty check`, `ruff check .` and `lint-imports` pass from the backend directory.
- The images are rebuilt with `build.sh`.
- `table-maintenance-db` is wiped and redeployed with `bootstrap.sh`.
- `validate.sh` and `task apps:validate KUBE_CONTEXT=retail-lakehouse` exit 0.
- `e2e.sh` passes against the new API paths.
  - The e2e tables `tm_e2e_*` already exist in Iceberg. The e2e must recreate its include rule and preset after the DB wipe; it is idempotent today.
- Commits are on `main`, unpushed, with conventional messages.

## Left to the builder

- **Task order and commit split.** Each commit must stay green. Moving one aggregate at a time is one option. Another is adding the tests with the expected failures and burning them down.
- **Exact names:** the intention port and its change values, the catalog `TableMetadata` type, and the maintenance-run API route shape.
- **Edge placements:** the observation types, the async loop bridge, `maintenance_procedure_args`, and anything else the placement rules leave ambiguous. Apply the rule, and put a one-line note in the plan when it was a judgment call.
- **The test tree.** `tests/` mirrors the new source tree.
