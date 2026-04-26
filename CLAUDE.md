# Project Guidelines

## Language

Respond in the same language as the user's message. The user typically communicates in Traditional Chinese (繁體中文) or English.

## Shell Commands

- Never use `cd` to change directory. Always use absolute paths or tool flags like `--directory`, `--project`.
- Use `uv run` instead of bare `python`, `python3`, `pytest`, or `pip`. Example: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

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
├── core/                    # Shared domain kernel
│   ├── application/
│   │   ├── domain/model/    # Entities, Value Objects, Domain Events, Exceptions
│   │   ├── port/inbound/    # Use case interfaces + result types
│   │   ├── port/outbound/   # Repository interfaces
│   │   └── service/         # Use case implementations (application services)
│   ├── adapter/
│   │   └── outbound/        # Repository implementations (SQL, K8s, in-memory)
│   ├── base/                # DDD shared kernel
│   └── configs/             # AppSettings, adapter enums
├── api/                     # API server entry
│   ├── adapter/
│   │   └── inbound/web/     # FastAPI routes, API DTOs
│   ├── dependencies/        # FastAPI dependency injection
│   └── main.py              # FastAPI app factory
├── scheduler/               # Scheduler entry
│   ├── main.py              # Scheduler bootstrap
│   └── scheduler_loop.py    # Polling loop
└── entrypoint.py            # ROLE env var → api or scheduler
```

### Rules

- **Domain** depends on nothing except `core/base/` and stdlib. No Pydantic — use dataclasses.
- **Application** depends on domain and base. No adapter, no framework, no infra imports.
- **Adapter** depends on application only (not domain directly). Web adapter catches application-layer exceptions, not domain exceptions.
- **Configs** (`core/configs/`) is cross-cutting configuration. It must not depend on any bounded context.
- **DTOs live in the adapter.** `JobApiRequest`/`JobApiResponse` are in `api/adapter/inbound/web/dto.py` with plain types (no domain enums).
- **Use case results live in the application layer.** Services convert domain objects to application-layer result dataclasses so adapters never see domain types.
- **Scheduler** cannot import from `api` or `fastapi` (enforced by import-linter).
- Architecture boundaries are enforced by `import-linter` (configured in `.importlinter`). Run `lint-imports` to verify.
- **Single image, dual role**: `ROLE=api` (default) or `ROLE=scheduler` via `entrypoint.py`.

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
- `Repository[E]` — generic persistence ABC
- `UseCase[TInput, TOutput]` — single `execute()` method
