# Project Guidelines

## Language

Respond in the same language as the user's message. The user typically communicates in Traditional Chinese (繁體中文) or English.

## Shell Commands

- Never use `cd` to change directory. Always use absolute paths or tool flags like `--directory`, `--project`.
- Use `uv run` instead of bare `python`, `python3`, `pytest`, or `pip`. Example: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
- The local minikube/dev cluster context is `retail-lakehouse`. Infra scripts (`*/bootstrap.sh`, `*/validate.sh`, `*/patch.sh`) require `KUBE_CONTEXT` to be set explicitly — there is no fallback (scripts fail fast with `KUBE_CONTEXT is required`). Always pass it when invoking Taskfile entries or running scripts directly, e.g. `task onboard KUBE_CONTEXT=retail-lakehouse`.

## Project Status (snapshot 2026-10-23 — update as work lands)

**What it is:** an Iceberg lakehouse platform on minikube plus a self-built Table Maintenance service (`src/table-maintenance`, DDD + Clean Architecture) that schedules Iceberg maintenance (compaction, snapshot expiry). Long-term vision: "GitHub for Data" DataOps SaaS.

**Data flow:** MySQL →(Debezium CDC)→ Kafka →(Iceberg Sink)→ Iceberg on MinIO, catalog = Polaris → queried by Trino. Polaris metrics reports also stream back to Kafka via Debezium (Postgres).

**History:**
- 2025-06 ~ 09: Trino, Kafka/Debezium/Iceberg CDC pipeline, monitoring stack.
- 2026-03 ~ 05: table-maintenance backend (API / scheduler / outbox messaging), naming conventions, import-linter layering.
- 2026-05 ~ 07: Polaris 1.5.0 + metrics reporter CDC to Kafka; Kafka 1 → 3 brokers; Iceberg sink static-membership fix; Kafka UI; Istio ambient (istiod / CNI / ztunnel) + Gateway API with wave-22 Gateway + HTTPRoutes; table-maintenance manifests moved `default` → `polaris` ns. The "Polaris events via OTEL → Kafka" attempt was fully reverted.

**Deployed on minikube** (via `bootstrap-by-scripts`):
- Wave 10: cert-manager, kube-prometheus, Strimzi
- Wave 11: KEDA, Spark Operator, OTel Operator, Istio base, Gateway API CRDs
- Wave 12: istiod, istio-cni, ztunnel
- Wave 20: Kafka (3 brokers), MinIO, MySQL, Polaris DB, Jaeger (trino / thanos)
- Wave 21–22: Polaris, 3 KafkaConnectors (debezium-mysql, iceberg-sink, polaris-cdc), `platform-gateway` + HTTPRoutes
- Wave 23: Trino, Kafka UI

**Not deployed / on hold (do not touch unless the user re-opens them):**
- `platform/25-*` + `src/table-maintenance` (table maintenance: backend / scheduler / db); not wired into `tasks/apps.yml`
- `platform/30-thanos`
- `platform/24-e2e-validation`
- ArgoCD path (`platform/00-argocd`, `01-argocd-health-checks`, `02-argocd-apps`, `charts/app-of-apps`)

**Current initiative: namespace re-layout** (one task at a time, each deployed + verified + committed on `main`; developer/reviewer agent prompts in `DEVELOPER_AGENT_PROMPT.md` / `REVIEWER_AGENT_PROMPT.md`):
1. `mysql`: `kafka-cdc` → `ecommerce-app`
2. `kafka-cdc` → `kafka`
3. `minio` → `object-storage`
4. `polaris` → `lakehouse-catalog`
5. `trino` → `lakehouse-query-engine`
6. Create `lakehouse-maintenance-operations`, `lakehouse-control-plane` namespaces, each inside the component wave that will later deploy its workloads (namespace only for now; no standalone "create namespaces" wave)
7. Create `temporal` namespace the same way, inside the future Temporal component wave
8. Full `task offboard` + `task onboard KUBE_CONTEXT=retail-lakehouse` end-to-end run

## Platform (Infra)

- `platform/<NN>-<component>/` — each wave dir has `bootstrap.sh` + `validate.sh` (some `patch.sh`); the `NN` prefix is the deploy order.
- `tasks/apps.yml` `bootstrap-by-scripts` / `validate` chain the waves; this is the active deploy path. `bootstrap-by-argocd` exists but is on hold.
- `task onboard` / `task offboard` create / destroy the whole colima + minikube cluster and run all waves.
- Kubernetes namespaces cannot be renamed: a "rename" means deploy into the new namespace, then delete the old one. Data loss on minikube is acceptable.

## Code Style

- **One object per file.** Each Python file exports one primary class, enum, or function. If a file grows to contain multiple exported objects, split it.
- **Descriptive filenames.** Name files after their primary export: `create_job.py` not `create.py`, `job_status.py` not `status.py`.
- **Package re-exports via `__init__.py`.** Expose a clean public API at the package level so consumers use `from models import JobRequest` instead of `from models.job_request import JobRequest`.
- **Intra-package: direct imports.** Within the same package, import from the module directly (e.g., `from models.job_status import JobStatus`) to avoid circular imports.
- **ABC over Protocol** for interface definitions. Use `abc.ABC` with `@abstractmethod`, not `typing.Protocol`.
- **StrEnum** for string-valued enumerations.
- **`from __future__ import annotations`** in every module for deferred type evaluation.

## Architecture Mindset

- **DDD best practices first.** Always prefer Domain-Driven Design idioms and patterns. When in doubt, choose the approach closest to established DDD literature (Evans, Vernon).
- **Design for high complexity.** This project will grow significantly in complexity. Favor extensible, well-structured designs over minimal implementations. Over-engineering is acceptable — under-engineering is not.

## Architecture: Clean Architecture (Strict Layering)

This project follows "Get Your Hands Dirty on Clean Architecture" with an additional **no-skip-layer rule**: each layer may only depend on the layer directly below it.

```
adapter/inbound  ──> application ──> domain
adapter/outbound ──> application ──> domain
                     application ──> base (shared kernel)
adapter/*        ──✗──> domain (forbidden: must go through application)
```

### Backend Structure

```
backend/
├── bootstrap/               # Composition roots (knows all layers)
│   ├── configs/             # AppSettings, adapter enums
│   ├── dependencies/        # FastAPI dependency injection
│   ├── api.py               # API entry point
│   ├── scheduler.py         # Scheduler entry point
│   └── messaging.py         # Outbox publisher entry point
├── adapter/                 # Outermost ring
│   ├── inbound/
│   │   ├── web/             # FastAPI routes, API DTOs
│   │   ├── scheduler/       # Scheduler polling loop
│   │   └── messaging/
│   │       └── outbox/      # Outbox publisher polling loop
│   └── outbound/            # Repository implementations (SQL, K8s, in-memory)
├── application/             # Middle ring
│   ├── domain/model/        # Entities, Value Objects, Domain Events, Exceptions
│   ├── port/inbound/        # Use case interfaces + result types
│   ├── port/outbound/       # Repository interfaces
│   └── service/             # Use case implementations (application services)
├── base/                    # DDD shared kernel
├── entrypoint.py            # GLAC_COMPONENT env var → api, scheduler, or messaging
└── tests/
```

### Rules

- **Domain** depends on nothing except `base/` and stdlib. No Pydantic — use dataclasses.
- **Application** depends on domain and base. No adapter, no framework, no infra imports.
- **Adapter** depends on application only (not domain directly). Web adapter catches application-layer exceptions, not domain exceptions.
- **Configs** (`bootstrap/configs/`) is cross-cutting configuration. It must not depend on any bounded context.
- **DTOs live in the adapter.** `JobApiRequest`/`JobApiResponse` are in `adapter/inbound/web/job/dto.py` with plain types (no domain enums).
- **Use case results live in the application layer.** Services convert domain objects to application-layer result dataclasses so adapters never see domain types.
- **Bootstrap** is the only layer allowed to import from all other layers. It is the composition root.
- Architecture boundaries are enforced by `import-linter` (configured in `src/table-maintenance/backend/.importlinter`). Run `lint-imports` to verify.
- **Single image, triple component**: `GLAC_COMPONENT=api` (default), `GLAC_COMPONENT=scheduler`, or `GLAC_COMPONENT=messaging` via `entrypoint.py`.
- **Unified settings**: All configuration via `GLAC_` prefixed env vars (pydantic-settings). Nested with `__` delimiter: `GLAC_SCHEDULER__INTERVAL_SECONDS=30`.

## Development Workflow

- **TDD always.** Write the failing test first, watch it fail, write minimal code to pass, then refactor. No exceptions.
- **Verify before commit.** Every commit must pass: `pytest -v`, `ty check`, `ruff check .`, `lint-imports`.
- **Semantic commits.** Use conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs(scope):`.
- **Incremental, atomic commits.** Each commit is independently valid — tests pass, linter clean.
- **Taskfile for automation.** `task pre-pr` runs all checks (pre-commit + unit-test + arch-test).

## Project Vision

This is being built as a **multi-tenant SaaS** platform. The current `jobs` bounded context is the first of several planned domains (customers, catalogs, tables, jobs, job runs). Design decisions should consider future extensibility across bounded contexts.

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

**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`, `Update`.

**Gateway directory structure** (under `port/outbound/{aggregate}/`):
```
{verb}_{noun}/
├── __init__.py       # re-export all symbols
├── gateway.py        # {Verb}{Noun}Gateway (extends Gateway)
├── input.py          # {Verb}{Noun}GatewayInput (optional, primitive-only)
└── output.py         # {Verb}{Noun}GatewayOutput (optional, primitive-only)
```

Input/output files must only use primitive types (`str`, `int`, `float`, `bool`, `dict`, `list`, `None`). They may import `base.value_object.ValueObject` but nothing from `application.domain` or other `base.*` modules. This is enforced by `test_outbound_port_structure.py`.

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

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, default strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
