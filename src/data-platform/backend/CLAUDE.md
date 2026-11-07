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

Everything below, except `base/`, `bootstrap/` and `entrypoint.py`, lives inside one bounded context, `context/<name>/`. Paths like `application/` and `adapter/` in the rules are relative to that context. Inside `application/` the order is `service` → `port` → `domain/service` → `domain/model`; a ring may import only rings below it, never above (contract `application-ring-order`).

### Backend Structure

Backend code is grouped by **bounded context** first. Inside a context, one **aggregate axis** runs through every layer: each layer directory is split into the same aggregate directories plus `shared` for what spans aggregates. For `table_maintenance` the aggregates are `table`, `table_discovery_rule`, `table_discovery_settings`, `table_maintenance_preset`, `table_maintenance_run`.

```
backend/
├── base/                         # DDD shared kernel (imports no context)
├── bootstrap/                    # Composition roots (knows every context)
│   ├── configs/                  # AppSettings, Component enum, adapter enums
│   ├── container/                # Wiring of services, ports and adapters
│   ├── api.py                    # GLAC_COMPONENT=api
│   ├── worker.py                 # GLAC_COMPONENT=worker (Temporal worker)
│   ├── event_consumer.py         # GLAC_COMPONENT=event_consumer
│   └── migrate.py                # GLAC_COMPONENT=migrate
├── context/
│   └── <name>/                   # One bounded context (today: table_maintenance)
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

Today there is one context, `table_maintenance`. `catalog` and `access` are planned next (see `docs/adr/0005-bounded-contexts-and-context-map.md`).

- **Independence rule.** Contexts are independent. A context's `application` imports no other context. A context may import another context only from its own outbound adapters (`adapter/outbound/` or `adapter/hybrid/<tech>/outbound/`), and only through that context's `application.port.inbound` (the outbound adapter calls the other context's use case and maps the result into its own types, anti-corruption style). Inbound adapters, hybrid `inbound` sides and hybrid `contracts` never import another context. Never through another context's domain, services, outbound ports or adapters. `bootstrap` may import every context; `base` imports no context. Enforced by `tests/architecture/test_context_independence.py` (an AST scan, because import-linter wildcards cannot say "another context").
- **No `context/shared`.** Contexts share code only through `base/`. Each keeps its own types (its own table-UUID value object) and links to other contexts by identifier values, not by shared classes.

### Adding a context

1. Create `context/<name>/__init__.py` and `context/<name>/{application,adapter}/`, and mirror them under `tests/context/<name>/`.
2. Create all four application rings: `service`, `port`, `domain/service` and `domain/model`. The `application-ring-order` layers contract uses `containers = context.*.application`, and import-linter requires every layer to exist in each container.
3. The architecture tests (`context_names()` in `tests/architecture/contexts.py`) and the `context.*` import-linter contracts pick the new context up without edits. Two guards keep it that way: no architecture test except `test_aggregates.py` names `table_maintenance`, and no contract names a concrete context.
4. Wire it in `bootstrap/`. A context that persists to SQL gets its own `adapter/outbound/shared/sql/` (its own metadata, `create_schema` and hand-written `AGGREGATE_SQL_PACKAGES`) with a mirrored drift test like `tests/context/table_maintenance/adapter/outbound/shared/sql/test_create_schema.py`. Never add one context's SQL packages to another context's list. `run_migrations` (`bootstrap/container/run_migrations.py`, called by `bootstrap/migrate.py`) calls each context's `create_schema`.

Known limitation: three architecture checks still expect every context to have the same adapter shape as `table_maintenance`: `test_directory_structure.py` (`ADAPTER_SUBDIRECTORIES`: web, event_consumer and temporal adapter directories), `test_temporal_workflow_determinism.py::test_workflow_modules_are_found` (at least one Temporal workflow) and `test_aggregate_axis.py::test_hybrid_outbound_dirs_are_found` (an `adapter/hybrid/temporal/outbound` directory). The concrete boundary samples live in `tests/context/table_maintenance/test_boundary_samples.py`, not in the generic rule. The project that adds the second context decides whether those checks become "only if present". The global `>= 5` in `test_every_aggregate_has_a_repository_port` is a follow-up (`docs/agents/known-follow-ups.md`).

### Rules

- **Domain** depends on nothing except `base/` and stdlib. No Pydantic — use dataclasses. Enforced by contract `domain-pure`.
- **Application** depends on domain and base, in ring order. No adapter, no bootstrap, no framework imports. Enforced by contracts `application-ring-order` and `application-no-outer-rings`.
- **Adapter** imports application only through ports and exceptions (not domain directly). Web adapter catches application-layer exceptions, not domain exceptions. Enforced by contract `adapters-see-only-ports`.
- **Adapter directions are independent.** `inbound`, `outbound` and `hybrid` do not import each other, a hybrid technology's `inbound` and `outbound` sides do not import each other, and inbound channels (`web`, `event_consumer`) are independent. Contracts `adapter-directions-separate`, `hybrid-directions-separate`, `inbound-channels-independent`. Layout: `tests/architecture/test_adapter_layout.py`.
- **Hybrid contracts** (`adapter/hybrid/<tech>/contracts/`) depend only on stdlib, base and ports, and only the same technology imports them. Contracts `hybrid-contracts-neutral`, `hybrid-contracts-private`. Temporal contracts are one package per workflow (`table_reconciliation`, `table_maintenance`, `table_maintenance_admission`, `table_discovery`) plus `shared` (task queue), each with short module names (`workflow_name.py`, `workflow_id.py`, `workflow_input.py`, `signal.py`, `activity.py`, `summary.py`); a signal lives with the workflow that receives it, an activity name with the workflow that calls it, and signal and activity names are StrEnums whose string values are pinned by `tests/context/table_maintenance/adapter/hybrid/temporal/contracts/test_wire_names.py`. Temporal workflows import only Temporal and their contracts: contract `temporal-workflows-sandbox-safe`, plus `tests/architecture/test_temporal_workflow_sandbox.py` (Temporal's own sandbox validation) and `test_temporal_workflow_determinism.py`.
- **Adapters do not import bootstrap**, and **Configs** (`bootstrap/configs/`) is cross-cutting: it must not depend on any bounded context. Contracts `adapters-no-bootstrap`, `configs-leaf`. **Base** depends on nothing project-internal: contract `base-isolation`. **Application exceptions** are a leaf: they import no other application ring, adapter or bootstrap (contract `application-exceptions-leaf`).
- **Aggregate axis.** Every layer directory is split by the same aggregate names, with no loose modules at a layer root (only the web adapter's `create_app.py` and `error_handlers.py`). Enforced by `tests/architecture/test_aggregate_axis.py`. A context's aggregates are derived: they are the directories under its `application/domain/model/` (except `shared`) whose package defines an `AggregateRoot` subclass (`tests/architecture/aggregates.py`, `aggregates(context)`), and every other layer may hold only those names plus `shared`. Adding an aggregate means adding its `AggregateRoot` and updating its context's `AGGREGATE_SQL_PACKAGES` in `adapter/outbound/shared/sql/create_schema.py` (guarded by that context's `test_create_schema.py`). `AGGREGATE_SQL_PACKAGES` is per context and stays hand-written.
- **Ports speak intent, not infrastructure.** Names in `application/` carry no infrastructure vocabulary (`temporal`, `workflow`, `signal`, `activity`, `spark`, `k8s`, `kubernetes`, `sql`, `pyiceberg`, `iceberg_rest`, `kafka`, `polaris`); a port names what the application wants (`SendTableChangeGateway` with a `TableChange`), the adapter picks the mechanism. Enforced by `tests/architecture/test_no_infrastructure_terms.py`.
- **Boundary-only imports.** A package with an `__init__.py` is a boundary; other packages import from it with `from <boundary> import Name`, never from a module inside it. Boundaries do not nest, and every module belongs to one (except the `bootstrap` entry modules `api`, `worker`, `event_consumer`, `migrate`). Enforced by `tests/architecture/test_import_boundary.py` (derived rules in `tests/architecture/boundaries.py`).
- **Import-linter has no exemptions.** `.importlinter` holds 14 named contracts and no `ignore_imports`. Enforced by `tests/architecture/test_importlinter_config.py`; run `lint-imports` to verify.
- **Ruff config only extends the root.** The backend `[tool.ruff]` extends the root `ruff.toml` and adds only isort first-party and flake8-type-checking lists; never add ignores, selects or rule-threshold overrides to the backend pyproject. Enforced by `tests/architecture/test_ruff_config.py`.
- **Naming and structure.** Inbound ports, outbound ports, services and web DTOs follow the naming tables below: `test_inbound_port_structure.py`, `test_outbound_port_structure.py`, `test_service_structure.py`, `test_dto_naming.py`; top-level layout `test_directory_structure.py`; inheritance depth `test_inheritance_depth.py`.
- **DTOs live in the adapter.** `CreateTableDiscoveryRuleApiRequest`/`TableDiscoveryRuleApiResponse` are in `adapter/inbound/web/table_discovery_rule/dto.py` with plain types (no domain enums).
- **Use case results live in the application layer.** Services convert domain objects to application-layer result dataclasses so adapters never see domain types.
- **Bootstrap** is the only layer allowed to import from all other layers. It is the composition root.
- **Single image, four components**: `GLAC_COMPONENT=api` (default), `worker`, `event_consumer`, or `migrate` via `entrypoint.py`.
- **Unified settings**: All configuration via `GLAC_` prefixed env vars (pydantic-settings). Nested with `__` delimiter: `GLAC_ADMISSION_LIMIT`, `GLAC_TEMPORAL__ADDRESS`.

## DDD Base Types (`base/`)

Shared kernel with zero external dependencies (stdlib only):
- `ValueObject` — frozen dataclass, equality by value
- `EntityId` — typed identifier (extends ValueObject)
- `Entity[ID]` — identity-based equality, `@dataclass(eq=False)`
- `AggregateRoot[ID]` — Entity + domain event collection
- `DomainEvent` — frozen dataclass with auto `occurred_at`
- `EventHandler[E]` — ABC for handling one domain event type
- `EventDispatcher` — concrete (non-subclassable) router from events to handlers
- `Repository[E]` — generic persistence ABC
- `Store` — infrastructure persistence (not aggregate)
- `Gateway` — external system interaction
- `UseCase[TInput, TOutput]` — single `execute()` method

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

A gateway directory may also hold extra single-class files (for example `list_input.py`). Except `list_input.py`, which defines `{Verb}{Noun}GatewayListInput`, each defines one class named after its file stem in CamelCase (`{CamelCaseStem}`), primitive-only like `input.py`. Enforced by `test_outbound_port_structure.py` (the extra files used to be an allowlist of fixed names).

Input/output files must only use primitive types (`str`, `int`, `float`, `bool`, `dict`, `list`, `None`). They may import `base.value_object.ValueObject` but nothing from `application.domain` or other `base.*` modules. This is enforced by `test_outbound_port_structure.py`.

Choosing between the three is decided by whether the thing is one of our aggregates, not by where its data lives (`docs/adr/0006-choosing-an-outbound-port.md`). An operation whose external system returns a secret only once is a `Create`/`Update` Gateway, not a Repository method (`docs/adr/0007-one-time-secrets.md`). The contexts and how they relate: `docs/adr/0005-bounded-contexts-and-context-map.md`.

See `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md` for full spec.

## DTO Naming Convention (Layer Suffixes)

Each DTO class carries a layer-specific suffix so its origin is unambiguous at a glance:

| Layer | File | Suffix | Example |
|-------|------|--------|---------|
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/input.py` | `UseCaseInput` | `CreateJobUseCaseInput` |
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/output.py` | `UseCaseOutput` (or `UseCaseOutputItem` for list helpers) | `CreateJobUseCaseOutput`, `ListJobsUseCaseOutputItem` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/input.py` | `GatewayInput` | `SubmitJobRunGatewayInput` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/output.py` | `GatewayOutput` | (none yet) |
| Web adapter | `adapter/inbound/web/{aggregate}/dto.py` | `ApiRequest` / `ApiResponse` | `CreateJobApiRequest`, `JobApiResponse` |

**Prefix rules:**
- Port layers (inbound/outbound): class prefix must match the PascalCase form of the parent directory name. Enforced by `test_inbound_port_structure.py` and `test_outbound_port_structure.py`.
- Web adapter: no prefix rule enforced. Verb prefix is convention for endpoint-specific request DTOs (e.g., `CreateJobApiRequest` over bare `JobApiRequest`); shared resource responses and nested sub-components may use noun-based names. Suffix enforced by `test_dto_naming.py`.

See `docs/superpowers/specs/2026-04-28-dto-naming-convention-design.md` for full spec.
