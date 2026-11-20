# Backend Architecture

## Clean Architecture (Strict Layering)

This project follows "Get Your Hands Dirty on Clean Architecture" with an additional **no-skip-layer rule**: each layer may only depend on the layer directly below it.

```
context.<name>.adapter/inbound  ──> application ──> domain
context.<name>.adapter/outbound ──> application ──> domain
context.<name>.adapter/hybrid   ──> application ──> domain
                                    application ──> base (shared kernel)
adapter/*  ──✗──> domain (forbidden: must go through application)
```

Everything below, except `base/`, `shared_kernel/`, `bootstrap/` and `entrypoint.py`, lives inside one bounded context, `context/<name>/`. Paths like `application/` and `adapter/` in the rules are relative to that context. Inside `application/` the order is `service` → `port` → `domain/service` → `domain/model`; a ring may import only rings below it, never above (contract `application-ring-order`).

### Backend Structure

Backend code is grouped by **bounded context** first. Inside a context, one **aggregate axis** runs through every layer: each layer directory is split into the same aggregate directories plus `shared` for what spans aggregates. For `table_maintenance` the aggregates are `catalog_discovery`, `table`, `table_discovery_rules`, `table_maintenance_policy`, `table_maintenance_policy_attachment`, `table_maintenance_run`, `table_reconciliation`; for `catalog` they are `catalog`, `namespace`, `table`, `generic_table`, `view`.

```
backend/
├── base/                         # DDD shared kernel (imports only shared_kernel from the project)
├── shared_kernel/                # Stdlib-only code shared by base and Temporal workflows
├── bootstrap/                    # Composition roots (knows every context)
│   ├── configs/                  # AppSettings, Component enum, adapter enums
│   ├── container/                # Wiring of services, ports and adapters
│   ├── api.py                    # GLAC_COMPONENT=api
│   ├── worker.py                 # GLAC_COMPONENT=worker (Temporal worker)
│   ├── event_consumer.py         # GLAC_COMPONENT=event_consumer
│   └── migrate.py                # GLAC_COMPONENT=migrate
├── context/
│   └── <name>/                   # One bounded context (today: table_maintenance, catalog)
│       ├── adapter/              # Outermost ring: inbound | outbound | hybrid
│       │   ├── inbound/
│       │   │   ├── web/{aggregate}/      # FastAPI routers, API DTOs
│       │   │   └── event_consumer/       # Polaris catalog event consumer loop
│       │   ├── outbound/{aggregate}/     # SQL, in-memory, catalog, Spark repo/store/gateway adapters
│       │   └── hybrid/                   # Technologies that are both directions
│       │       └── temporal/
│       │           ├── inbound/          # Workflows, activities, schedule setup
│       │           ├── outbound/{aggregate}/  # Signal, start and schedule gateways
│       │           └── contracts/        # Workflow names/IDs, signals, workflow inputs
│       └── application/          # Middle ring
│           ├── domain/model/{aggregate}/ # Entities, Value Objects, Domain Events
│           ├── domain/service/{aggregate}/  # Domain services (planning, rule matching)
│           ├── port/inbound/{aggregate}/ # Use case interfaces + input/output types
│           ├── port/outbound/{aggregate}/  # Repo, Store and Gateway interfaces
│           ├── service/{aggregate}/      # Use case implementations
│           └── exceptions/               # Application-layer exceptions
├── entrypoint.py                 # GLAC_COMPONENT env var → api, worker, event_consumer, or migrate
└── tests/
    ├── architecture/             # Rules that run once per context, plus context independence
    ├── base/
    ├── bootstrap/
    └── context/<name>/{application,adapter,fakes}/   # Mirrors the context
```

Import paths carry the context prefix: `context.table_maintenance.application.port...`. `context/` and `context/<name>/` are structural packages (a docstring, no exports, not boundaries).

### Bounded Contexts

Today there are two contexts. `table_maintenance` schedules Iceberg maintenance and persists to SQL. `catalog` serves catalogs, namespaces, tables, generic tables and views with Polaris as the source of truth: each aggregate's `{Aggregate}Repo` has a Polaris HTTP adapter (`adapter/outbound/<aggregate>/polaris/`), nothing is cached, and Polaris errors map to the application exceptions (`NotFoundError` 404, `ConflictError` 409, `ValidationError` 422, `PermissionDeniedError` 403, `CatalogUnavailableError` 502) with Polaris's message as the detail. Every Polaris mapper reads its reply through `read_polaris_reply` (`adapter/outbound/shared/polaris/`), so a reply it cannot read is a 502, never a 500, and required fields are never defaulted. The id value objects refuse U+001F, which joins their parts. `access` is planned next (see `docs/adr/0005-bounded-contexts-and-context-map.md`).

- **Independence rule.** Contexts are independent. A context's `application` imports no other context. A context may import another context only from its own outbound adapters (`adapter/outbound/` or `adapter/hybrid/<tech>/outbound/`), and only through that context's `application.port.inbound` (the outbound adapter calls the other context's use case and maps the result into its own types, anti-corruption style). Inbound adapters, hybrid `inbound` sides and hybrid `contracts` never import another context. Never through another context's domain, services, outbound ports or adapters. `bootstrap` may import every context; `base` imports no context. Enforced by `tests/architecture/test_context_independence.py` (an AST scan, because import-linter wildcards cannot say "another context").
- **No `context/shared`.** Contexts share code only through `base/` and `shared_kernel/`. Each keeps its own types (its own table-UUID value object) and links to other contexts by identifier values, not by shared classes.

**A table has one maintenance workflow, started by its reconciliation, and its attempts go straight to Volcano.** The `TableReconciliationWorkflow` (`table-reconciliation:table-uuid={uuid}`) plans and starts a `TableMaintenanceWorkflow` child under `table-maintenance:table-uuid={uuid}` (`ALLOW_DUPLICATE`), which runs the planned operations in order, one Spark job each; run ids stay `mr-`. After a run reports, the next run is started only once its workflow closed (bounded by the report activity's worst case; a refused start is recorded `run_start_failed`). An attempt is `queued` until its driver starts; its deadline (`attempt_deadline_seconds`) runs from that start, and one still queued at its own queue wait limit (`queue_wait_limit_seconds`) is polled once more and, still without a driver start, ends `queue_timed_out`. A manual run on a table with a run in flight starts no second run: it raises that run's priority, only upward, and an attempt still `queued` whose job reads `PENDING` is requeued under the same attempt number. The consumed manual trigger is given back, and planned as a run of its own after this one, when the run left the raise unapplied (it arrived after the run's last attempt ended, or its record failed), received fewer raises than the reconciliation delivered, or closed without reporting (a run that does is treated as finished at once); it is dropped when the plan fails, the table is skipped, nothing is planned or the workflow is stopping. A changed table priority applies from the next plan. Run-time detail (polling, fencing, requeue, bounds) is in `platform/25-lakehouse-control-plane/README.md`.

**A table's last commit and last discovery are observations, not maintenance state** (neither moves `updated_at`). `Table.last_committed_at` is the newest snapshot's commit time, moved only forward wherever the backend reads the table from the catalog: discovery, a catalog event (`ProcessTableHint`) and a reconcile's observation. When only the commit moved, `TablesRepo.record_last_commit` writes that one column (forward-only, never on a dropped table), so a writer holding an older copy never puts back the rest of the row; a full `update` never moves the stored last commit back either. Discovery saves a table only when something about it changed, so instead of a per-table "seen" time a completed catalog-wide scan records one `CatalogDiscovery` per catalog; a live table's last discovery is that time (or its registration, if later), and a table the scan drops keeps the previous scan's time in `Table.last_discovered_at`.

**A table's properties are shown against a catalogue of known Iceberg properties** (`iceberg_table_property_catalogue()` in `context/catalog/application/domain/model/table/`): each entry has its Iceberg default, a description and whether a reset may touch it, pinned to one Iceberg version (today 1.10.1, the Spark runtime's `GLAC_SPARK__ICEBERG_VERSION` and Polaris 1.8.0's); update the defaults with that version. `resolve_table_properties` gives every catalogue key, every key the table sets and every key the catalog defaults a default: the catalog's `table-override.<key>` (forced, never resettable), else its `table-default.<key>`, else Iceberg's. A reset (`POST …/tables/{table}/properties/reset`) goes through the uuid-guarded property update: it removes a key, but writes the default back when a new table would hold it explicitly (a catalog default, which Polaris applies only at create, and `write.parquet.compression-codec`, which Iceberg writes on every new table). A key is modified when its value differs from its default, or, unset, when the reset would write the default (the default shown does not apply); a custom key is modified only when it has no default or is off it. `created-at` is written by Polaris (`set_by_catalog`): no default, never modified. `format-version`, `gc.enabled`, `created-at` and forced keys refuse the whole reset with 422.

### Adding a context

1. Create `context/<name>/__init__.py` and `context/<name>/{application,adapter}/`, and mirror them under `tests/context/<name>/`.
2. Create all four application rings: `service`, `port`, `domain/service` and `domain/model`. The `application-ring-order` layers contract uses `containers = context.*.application`, and import-linter requires every layer to exist in each container.
3. The architecture tests (`context_names()` in `tests/architecture/contexts.py`) and the `context.*` import-linter contracts pick the new context up without edits. Two guards keep it that way: no architecture test except `test_aggregates.py` names `table_maintenance`, and no contract names a concrete context.
4. Wire it in `bootstrap/`. Its web adapter exposes `register_routes(app, use_cases)` in `adapter/inbound/web/register_routes.py`, which keeps its use cases on `app.state` under its own key, adds its error handlers and mounts its routers under `/v1`; `bootstrap/container/build_api_app.py` passes one registration per context to `create_api_app`, so all contexts share one FastAPI app. A context that persists to SQL gets its own `adapter/outbound/shared/sql/` (its own metadata, `create_schema` and hand-written `AGGREGATE_SQL_PACKAGES`) with a mirrored drift test like `tests/context/table_maintenance/adapter/outbound/shared/sql/test_create_schema.py`. Never add one context's SQL packages to another context's list. `run_migrations` (`bootstrap/container/run_migrations.py`, called by `bootstrap/migrate.py`) calls each context's `create_schema`.
5. A context must have `adapter/inbound/web` and `adapter/outbound`. `adapter/inbound/event_consumer` and `adapter/hybrid/<tech>` are optional; a hybrid technology directory that exists holds exactly `inbound`, `outbound` and `contracts`. Every aggregate has exactly one repository port in its own context (`test_each_aggregate_has_one_repository_port_per_context`).

### Rules

- **Domain** depends only on the stdlib, `base` and Pydantic (`pydantic`, `pydantic_core`, `annotated_types`). Enforced by `test_domain_dependencies.py` (allow-list) and contract `domain-pure`.
- **Application** depends on domain and base, in ring order. No adapter, no bootstrap, no framework imports. Services, ports and exceptions do not import Pydantic directly; they reach it only through the domain and `base` (ports through `UseCaseInput` / `UseCaseOutput`, `docs/adr/0010-pydantic-in-inbound-ports.md`). Enforced by contracts `application-ring-order`, `application-no-outer-rings` and `application-outer-rings-pydantic-free`.
- **Adapter** imports application only through ports and exceptions (not domain directly). Web adapter catches application-layer exceptions, not domain exceptions. Enforced by contract `adapters-see-only-ports`.
- **Adapter directions are independent.** `inbound`, `outbound` and `hybrid` do not import each other, a hybrid technology's `inbound` and `outbound` sides do not import each other, and inbound channels (`web`, `event_consumer`) are independent. Contracts `adapter-directions-separate`, `hybrid-directions-separate`, `inbound-channels-independent`. Layout: `tests/architecture/test_adapter_layout.py`.
- **Hybrid contracts** (`adapter/hybrid/<tech>/contracts/`) depend only on stdlib, base and ports, and only the same technology imports them. Contracts `hybrid-contracts-neutral`, `hybrid-contracts-private`. Temporal contracts are one package per workflow (`table_reconciliation`, `table_maintenance`, `table_discovery`) plus `shared` (task queue, `TableSearchAttribute` names of the search attributes registered by `platform/21-temporal`), each with short module names (`workflow_name.py`, `workflow_id.py`, `workflow_input.py`, `signal.py`, `activity.py`, `summary.py`); a signal lives with the workflow that receives it, an activity name with the workflow that calls it, and signal and activity names are StrEnums whose string values are pinned by `tests/context/table_maintenance/adapter/hybrid/temporal/contracts/test_wire_names.py`. Activities are grouped by workflow: each contract package's `XActivity` enum has exactly one `XActivities` class in `inbound/activities/` (`TableReconciliationActivities`, `TableMaintenanceActivities`, `TableDiscoveryActivities`) holding every method that enum names, and that class takes the constructor dependencies its methods use. Each method wraps exactly one inbound port, except the signal wiring (`SIGNAL_PARENT`, `GET_WORKFLOW_RUNNING`), which calls the Temporal client instead. Enforced by `tests/architecture/test_temporal_activity_grouping.py`. Temporal workflows import only Temporal, their contracts and `shared_kernel`: contract `temporal-workflows-sandbox-safe`, plus `tests/architecture/test_temporal_workflow_sandbox.py` (Temporal's own sandbox validation) and `test_temporal_workflow_determinism.py`.
- **Adapters do not import bootstrap**, and **Configs** (`bootstrap/configs/`) is cross-cutting: it must not depend on any bounded context. Contracts `adapters-no-bootstrap`, `configs-leaf`. **Base** depends on nothing project-internal except `shared_kernel`: contract `base-isolation` (its forbidden list is every other root package, `test_base_may_import_only_the_shared_kernel`). **Application exceptions** are a leaf: they import no other application ring, adapter or bootstrap (contract `application-exceptions-leaf`).
- **Aggregate axis.** Every layer directory is split by the same aggregate names, with no loose modules at a layer root (only the web adapter's `register_routes.py` and `error_handlers.py`). Enforced by `tests/architecture/test_aggregate_axis.py`. A context's aggregates are derived: they are the directories under its `application/domain/model/` (except `shared`) whose package defines an `AggregateRoot` subclass (`tests/architecture/aggregates.py`, `aggregates(context)`), and every other layer may hold only those names plus `shared`, except `application/port/inbound`, which mirrors the service aggregates without `shared` (`test_inbound_ports_match_services`). A context-wide read model's use case files under the aggregate that owns its route; today platform settings sits under `table_maintenance_run`. Adding an aggregate means adding its `AggregateRoot` and updating its context's `AGGREGATE_SQL_PACKAGES` in `adapter/outbound/shared/sql/create_schema.py` (guarded by that context's `test_create_schema.py`). `AGGREGATE_SQL_PACKAGES` is per context and stays hand-written.
- **Ports speak intent, not infrastructure.** Names in `application/` carry no infrastructure vocabulary (`temporal`, `workflow`, `signal`, `activity`, `spark`, `k8s`, `kubernetes`, `sql`, `pyiceberg`, `iceberg_rest`, `kafka`, `polaris`); a port names what the application wants (`SendTableChangeGateway` with a `TableChange`), the adapter picks the mechanism. Enforced by `tests/architecture/test_no_infrastructure_terms.py`.
- **Boundary-only imports.** A package with an `__init__.py` is a boundary; other packages import from it with `from <boundary> import Name`, never from a module inside it. Boundaries do not nest, and every module belongs to one (except the `bootstrap` entry modules `api`, `worker`, `event_consumer`, `migrate`). Enforced by `tests/architecture/test_import_boundary.py` (derived rules in `tests/architecture/boundaries.py`).
- **Import-linter has no exemptions.** `.importlinter` holds 16 named contracts and no `ignore_imports`. Enforced by `tests/architecture/test_importlinter_config.py`; run `lint-imports` to verify.
- **Ruff config only extends the root.** The backend `[tool.ruff]` extends the root `ruff.toml` and adds only isort first-party and flake8-type-checking lists; never add ignores, selects or rule-threshold overrides to the backend pyproject. Enforced by `tests/architecture/test_ruff_config.py`.
- **Long import heads keep `# noqa: E501`.** A `from <module> import (` head that cannot fit in 120 characters (long port and adapter paths that follow the naming rules) carries `# noqa: E501`; the owner accepted these markers on 2026-11-07, so do not rename modules to shorten them. Any other line must fit.
- **Naming and structure.** Inbound ports, outbound ports, services and web DTOs follow the naming tables below: `test_inbound_port_structure.py` and `test_inbound_port_models.py`, `test_outbound_port_structure.py`, `test_service_structure.py`, `test_dto_naming.py`; top-level layout `test_directory_structure.py`; inheritance depth `test_inheritance_depth.py`.
- **DTOs live in the adapter.** `ReplaceTableDiscoveryRulesApiRequest`/`TableDiscoveryRulesApiResponse` are in `adapter/inbound/web/table_discovery_rules/dto.py` with plain types (no domain enums).
- **Use case results live in the application layer.** Services convert domain objects to `UseCaseOutput` models (ADR 0010) so adapters never see domain types.
- **Bootstrap** is the only layer allowed to import from all other layers. It is the composition root.
- **Single image, four components**: `GLAC_COMPONENT=api` (default), `worker`, `event_consumer`, or `migrate` via `entrypoint.py`.
- **Unified settings**: All configuration via `GLAC_` prefixed env vars (pydantic-settings). Nested with `__` delimiter: `GLAC_MAINTENANCE_MAX_ATTEMPTS`, `GLAC_TEMPORAL__ADDRESS`.

## DDD Base Types (`base/`)

Shared kernel on Pydantic v2 (stdlib, `pydantic`, `pydantic_core`, `annotated_types`, and `shared_kernel` from the project). Import everything from `base`.

The domain model types, all strict (no coercion: `True` is not an `int`, a `list` is not a `tuple`, a plain `str` is not a `StrEnum`) and `extra="forbid"`:
- `ValueObject` — frozen, equality by value. A subclass declares fields, no decorator: `class Money(ValueObject): amount: int; currency: str`. Invariants go in `field_validator` / `model_validator(mode="after")` raising plain `ValueError`. Wire input goes through `Money.from_primitives(data)` (strict JSON mode, only the wire names / aliases are accepted); wire output through `to_primitives()` (JSON primitives keyed by alias). Never `model_validate` wire data directly.
- `EntityId` — a `RootModel[str]`, frozen, built positionally: `class OrderId(EntityId): pass`, `OrderId("1")`; `.value` gives the string. Ids of different kinds never compare equal. An id kind this platform mints declares `PREFIX: ClassVar[str | None] = "mr"` (ADR 0011): every construction path then refuses any value but `mr-<26 base32 characters>` with `InvariantViolation` (`TableMaintenanceRunId must look like mr-<26 base32 characters>`), and `TableMaintenanceRunId.new()` mints one (`TypeError` without a `PREFIX`; a bad `PREFIX` raises `ValueError` when the class is defined). `PREFIX` is a class variable, so the dump, JSON and `str` stay the bare string. Without `PREFIX` any string is accepted. Every context id type is listed in `tests/architecture/test_prefixed_ids.py` as `EXPECTED_PREFIXES` (with its prefix), `UNPREFIXED` or `PENDING` (to be prefixed; may not exist yet), and no prefix is used twice; a new id type gets a row there.
- `Entity[ID]` — `class User(Entity[UserId]): name: str`; equal and hashed by class and `id`. `validate_assignment=True`, and an assignment is atomic: a rejected one (field or cross-field after-validator) leaves the entity unchanged. Fields checked together by a cross-field validator are changed in one step with `self._assign_together(a=..., b=...)` (only the changed fields), never one after the other and never through `__dict__`. Reassign containers (`self.x = (*self.x, v)`) instead of mutating them in place.
- `AggregateRoot[ID]` — `class Order(AggregateRoot[OrderId]): total: int`; an Entity that records events with `register_event()` and hands them over with `collect_events()` (a private attribute, never dumped or compared).
- `DomainEvent` — frozen, `class OrderPlaced(DomainEvent): order_id: str`; `occurred_at` defaults to now (UTC).
- `ValueObject.with_changes(**changes)` — a changed copy of a value object that runs every validator. Domain code never calls `model_copy` (it skips validation), and never copies an aggregate (pending events would be lost).
- `InvariantViolation` — the `ValueError` the model bases raise, chained from Pydantic's error, on these paths: construction (including `EntityId("…")`), `from_primitives`, `model_validate` / `model_validate_json`, `with_changes`, and entity attribute assignment (including `_assign_together`). Validating a base through a Pydantic `TypeAdapter` raises Pydantic's own error; adapters never do this, and they never import the domain directly (contract `adapters-see-only-ports`). The violation's text is one line, the first error as `<dotted.loc>: <msg>` (just `<msg>` for a model-level rule); an inner model's violation raised inside an outer validator comes out of the outer model as one violation. Services use `str(exc)` and never import Pydantic. A broken invariant answers 422 with that line; `InvalidTableTransition` / `InvalidRunTransition` still answer 409. Tests expect `pytest.raises(InvariantViolation)`, never Pydantic's `ValidationError`.
- `UseCaseInput` / `UseCaseOutput` — the inbound port models (ADR 0010): frozen, strict, `extra="forbid"`, raising `AttributeError` like the model bases. A refused input raises `InvariantViolation`; a refused output raises builtin `TypeError` chained from Pydantic's error, because only our services build outputs, so a refused one is a server bug: no edge handler catches it, and it surfaces as a logged 500, a retryable Temporal failure, or a hint the consumer retries and logs. Tests expect `pytest.raises(TypeError)` for a refused output. Fields hold primitives and stdlib types only (`str`, `int`, `float`, `bool`, `None`, `datetime`, `timedelta`, `tuple`, `dict`) and classes nested one level inside, each extending the same base and named by what it holds (`ListTableCommitsUseCaseOutput.Commit`); never a domain type. An entry point holding a dict of JSON primitives builds an input with `{Name}UseCaseInput.from_primitives(data)` (strict JSON mode: ISO strings become `datetime`, arrays `tuple`), a tolerant reader that ignores unknown keys at every depth but refuses missing or mistyped ones, so a newer workflow's extra key does not break an older worker during a rolling deploy; code builds by keyword, where an extra key is still refused. An `InvariantViolation` at an edge is a client error, like `ValidationError`: 422 from each context's web error handlers, a non-retryable Temporal `ApplicationError`, a hint the event consumer drops without retry. Each `input.py` / `output.py` defines one top-level class and the use case's `__init__.py` exports exactly its three names, checked for every use case by `tests/architecture/test_inbound_port_models.py`.
- **Rules for writing port models** (ADR 0010, `docs/adr/0010-pydantic-in-inbound-ports.md`):
  - A sequence field is `tuple[...]`, never `list[...]` or `set[...]` (strict mode refuses a `list` for a `tuple`; `from_primitives` turns a JSON array into a `tuple`). A field holds only `str`, `int`, `float`, `bool`, `None`, `datetime`, `timedelta`, a `Literal`, a `tuple[...]` or `dict[...]` of these, a class nested in the same port file, or a union of these; `Any` only inside a `dict` or `tuple`. Enforced by `tests/architecture/test_inbound_port_field_types.py`.
  - A structured dict (a settings blob, a Spark request, an Iceberg schema or summary) stays `dict[str, Any]`; do not invent a nested model for what the application only passes through.
  - A nested type is a class nested in the input or output, named by its noun (`ListTableCommitsUseCaseOutput.Commit`, `PlanTableMaintenanceUseCaseOutput.Check`), at most one level deep, never a second top-level `…Item` class. Do not add a `…Item` class.
  - `from_primitives` is a tolerant reader: it ignores unknown keys at every depth and still refuses missing or mistyped ones. Use it for what another process wrote (a Temporal payload, an event); build by keyword in code, where an unknown key is refused.
  - A port field is never named after a `BaseModel` attribute (`schema`, `json`, `copy`, `dict`, `validate`, `construct`) or a port base attribute (`from_primitives`); name it by what it holds (`table_schema`, `view_schema`). Enforced by `tests/architecture/test_inbound_port_field_names.py`.
  - Do not edit a web DTO's docstring casually: the docstrings of `ApiRequest` / `ApiResponse` classes and their fields are the descriptions in the published OpenAPI document, which the console's generated client is built from (the `gates:pre-pr` contract test fails on a change). Change one only when the published description should change.
- Assigning to a frozen model (`ValueObject`, `DomainEvent`, `EntityId`) and `del` of a field of any model (an `Entity` too) raise Python's builtin `AttributeError`, not `InvariantViolation`: a mutation is a programming error, so it surfaces as a 500, not a 422. The message names the class; a value object's points at `with_changes`. Tests expect `pytest.raises(AttributeError, match="is immutable")` for frozen assignment.

`base` exports only the allowlisted building blocks: `ValueObject`, `Entity`, `EntityId`, `AggregateRoot`, `DomainEvent`, `InvariantViolation`, `Specification`, `Repository`, `Store`, `Gateway`, `UseCase`, `UseCaseInput`, `UseCaseOutput`, `EventHandler`, `EventDispatcher`, `UnitOfWork` (not all exist yet). Helpers and shared types such as `WholeSeconds` belong to the context that uses them. Private `_` modules in `base/` are implementation details used only inside `base/`; nothing outside imports them. Both rules are enforced by `tests/architecture/test_base_building_blocks.py`. To add to `base`, edit the allowlist in `tests/architecture/test_base_building_blocks.py` and say why here.

Concrete domain types extend these bases directly (max depth 1, checked at class creation and by `test_inheritance_depth.py`). The five model bases and the two port model bases are listed in ruff's `runtime-evaluated-base-classes` (`test_every_pydantic_base_is_runtime_evaluated`), so field-type imports stay at runtime; import the base from `base`, never `pydantic.BaseModel` directly.

The ports and helpers:
- `EventHandler[E]` — ABC for handling one domain event type
- `EventDispatcher` — concrete (non-subclassable) router from events to handlers
- `Repository[E]` — generic persistence ABC
- `Store` — infrastructure persistence (not aggregate)
- `Gateway` — external system interaction
- `UseCase[TInput, TOutput]` — single `execute()` method

## Shared Kernel (`shared_kernel/`)

A small top-level package beside `base/`, for code that both `base` and Temporal workflow contracts need. Temporal workflows may not import `base` or Pydantic (contract `temporal-workflows-sandbox-safe`), so anything a workflow shares with `base` lives here. It uses the standard library only: it imports no `base`, `bootstrap`, `context`, third-party package or sibling project package (contract `shared-kernel-stdlib-only`, `tests/architecture/test_shared_kernel_stdlib_only.py`). Anything may import it: `base`, contexts (any layer), `bootstrap`, Temporal contracts and workflows. Import from `shared_kernel`, never from its modules; modules starting with `_` are private to the package. Keep it small: add to it only what two parts that cannot import each other must share.

- `prefixed_id_from_parts(prefix, unix_ms, random_bits)` — a prefixed id such as `mr-01h455vb4pex5vsknk084sn02q`: the prefix, a dash and a UUIDv7 as 26 lowercase Crockford base32 characters (the TypeID suffix encoding). Deterministic, so a workflow passes `int(workflow.now().timestamp() * 1000)` and `workflow.random().getrandbits(74)`. The prefix is 2 to 8 lowercase letters, else `ValueError`.
- `new_prefixed_id(prefix)` — the same with `uuid.uuid7()`, for code that may use the clock and the system random source.
- `prefixed_id_pattern(prefix)` — the compiled pattern `^<prefix>-[0-7][0-9a-hjkmnp-tv-z]{25}$`.

The format and the prefix list are in `docs/adr/0011-prefixed-resource-ids.md`.

## Outbound Port & Adapter Naming Convention

Three base classes define all outbound ports (in `base/`):

| Base Class | When to use | Port format | Adapter format |
|------------|------------|-------------|----------------|
| `Repository` | Aggregate persistence | `{Aggregate}Repo` | `{Aggregate}{Tech}Repo` |
| `Store` | Infrastructure persistence (not aggregate) | `{Noun}Store` | `{Noun}{Tech}Store` |
| `Gateway` | External system interaction | `{Verb}{Noun}Gateway` | `{Verb}{Noun}{Tech}Gateway` |

**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`, `Update`, `Create`.

**Gateway directory structure** (under `port/outbound/{aggregate}/`):
```
{verb}_{noun}/
├── __init__.py       # re-export all symbols
├── gateway.py        # {Verb}{Noun}Gateway (extends Gateway)
├── input.py          # {Verb}{Noun}GatewayInput (optional, primitive-only)
└── output.py         # {Verb}{Noun}GatewayOutput (optional, primitive-only)
```

A gateway directory may also hold extra single-class files (for example `list_input.py`). Except `list_input.py`, which defines `{Verb}{Noun}GatewayListInput`, each defines one class named after its file stem in CamelCase (`{CamelCaseStem}`), primitive-only like `input.py`. The extra file names are the fixed allowlist `GATEWAY_EXTRA_FILES` in `test_outbound_port_structure.py`, which enforces this.

Input/output files must only use primitive types (`str`, `int`, `float`, `bool`, `dict`, `list`, `None`). They may import `base.value_object.ValueObject` but nothing from `application.domain` or other `base.*` modules. One exception: `output.py` may import the extra files of its own gateway directory (for example `job_container_exit.py`, a list item of the output), since those are held to the same primitive-only rule. This is enforced by `test_outbound_port_structure.py`.

Choosing between the three is decided by whether the thing is one of our aggregates, not by where its data lives (`docs/adr/0006-choosing-an-outbound-port.md`). An operation whose external system returns a secret only once is a `Create`/`Update` Gateway, not a Repository method (`docs/adr/0007-one-time-secrets.md`). The contexts and how they relate: `docs/adr/0005-bounded-contexts-and-context-map.md`.

See `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md` for full spec.

## DTO Naming Convention (Layer Suffixes)

Each DTO class carries a layer-specific suffix so its origin is unambiguous at a glance:

| Layer | File | Suffix | Example |
|-------|------|--------|---------|
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/input.py` | `UseCaseInput` (the class extends `UseCaseInput`) | `CreateJobUseCaseInput` |
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/output.py` | `UseCaseOutput`; a nested type is a nested class named by its noun, not a second top-level class | `CreateJobUseCaseOutput`, `ListTableCommitsUseCaseOutput.Commit` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/input.py` | `GatewayInput` | `SubmitJobRunGatewayInput` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/output.py` | `GatewayOutput` | (none yet) |
| Web adapter | `adapter/inbound/web/{aggregate}/dto.py` | `ApiRequest` / `ApiResponse` | `CreateJobApiRequest`, `JobApiResponse` |

**Prefix rules:**
- Port layers (inbound/outbound): class prefix must match the PascalCase form of the parent directory name. Enforced by `test_inbound_port_models.py` (inbound input and output), `test_inbound_port_structure.py` (inbound use case) and `test_outbound_port_structure.py`.
- Web adapter: no prefix rule enforced. Verb prefix is convention for endpoint-specific request DTOs (e.g., `CreateJobApiRequest` over bare `JobApiRequest`); shared resource responses and nested sub-components may use noun-based names. Suffix enforced by `test_dto_naming.py`.

See `docs/superpowers/specs/2026-04-28-dto-naming-convention-design.md` for full spec.
