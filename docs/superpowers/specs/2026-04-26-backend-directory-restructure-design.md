# Backend Directory Restructure Design

**Date:** 2026-04-26
**Status:** Approved
**Scope:** Reorganize backend directory structure to reflect hexagonal architecture layers

## Problem

The current backend directory structure has several inconsistencies:

1. **Inbound adapters are scattered at the top level** (`api/`, `scheduler/`, `outbox_publisher/`) while outbound adapters are nested inside `core/adapter/outbound/`.
2. **`core/` is semantically ambiguous** — it mixes application, domain, adapter/outbound, base, and configs, but adapters should not be part of "core."
3. **Composition roots are scattered** — `api/main.py`, `scheduler/main.py`, `outbox_publisher/main.py`, and `dependencies/` are all separate top-level directories doing the same job (wiring dependencies).
4. **`configs/` is only used by composition roots** but sits at the same level as domain code.

## Design

Reorganize so that each top-level directory corresponds to one hexagonal architecture concept.

### Target Structure

```
backend/
├── bootstrap/                     # Composition root (knows all layers)
│   ├── configs/                   # AppSettings, adapter enums
│   ├── dependencies/              # FastAPI DI wiring
│   ├── api.py                     # API entry point
│   ├── scheduler.py               # Scheduler entry point
│   └── messaging.py               # Outbox publisher entry point
├── adapter/                       # Outermost ring
│   ├── inbound/
│   │   ├── web/                   # FastAPI routes, DTOs
│   │   ├── scheduler/             # Scheduler polling loop
│   │   └── messaging/
│   │       └── outbox/            # Outbox publisher polling loop
│   └── outbound/                  # Repository implementations (SQL, K8s, in-memory)
├── application/                   # Middle ring
│   ├── domain/model/              # Entities, Value Objects, Domain Events
│   ├── port/
│   │   ├── inbound/              # Use case interfaces + result types
│   │   └── outbound/             # Repository interfaces
│   ├── service/                   # Use case implementations
│   └── exceptions.py
├── base/                          # Shared kernel (stdlib only)
├── entrypoint.py                  # ROLE dispatch
└── tests/
```

### Migration Map

| Current | Target |
|---|---|
| `core/application/` | `application/` |
| `core/base/` | `base/` |
| `core/configs/` | `bootstrap/configs/` |
| `core/adapter/outbound/` | `adapter/outbound/` |
| `api/adapter/inbound/web/` | `adapter/inbound/web/` |
| `api/main.py` | `bootstrap/api.py` |
| `scheduler/main.py` | `bootstrap/scheduler.py` |
| `scheduler/scheduler_loop.py` | `adapter/inbound/scheduler/scheduler_loop.py` |
| `outbox_publisher/main.py` | `bootstrap/messaging.py` |
| `outbox_publisher/publisher_loop.py` | `adapter/inbound/messaging/outbox/publisher_loop.py` |
| `dependencies/` | `bootstrap/dependencies/` |

### Directories Eliminated

- `core/` — replaced by top-level `application/`, `base/`, and moves to `adapter/`, `bootstrap/`
- `api/` — split into `adapter/inbound/web/` and `bootstrap/api.py`
- `scheduler/` — split into `adapter/inbound/scheduler/` and `bootstrap/scheduler.py`
- `outbox_publisher/` — split into `adapter/inbound/messaging/outbox/` and `bootstrap/messaging.py`
- `dependencies/` — moved to `bootstrap/dependencies/`

### Dependency Rules

| Directory | May depend on | Must not depend on |
|---|---|---|
| `base/` | stdlib only | everything else |
| `application/domain/` | base | application services, adapter, bootstrap |
| `application/` (port, service) | domain, base | adapter, bootstrap |
| `adapter/` | application, base | bootstrap |
| `bootstrap/` | all layers | — |

### Inbound Adapter Categorization

Inbound adapters are grouped by driving mechanism:

| Directory | Driving mechanism | Examples |
|---|---|---|
| `adapter/inbound/web/` | HTTP requests | FastAPI routes |
| `adapter/inbound/scheduler/` | Timer / cron | Polling loop |
| `adapter/inbound/messaging/` | Messages / events | Outbox poller, future Kafka consumer |

The `messaging/` directory uses technology-specific subdirectories (`outbox/`, future `kafka/`, etc.) so the top-level grouping remains stable as new messaging technologies are added.

## Impact

- All import paths change (every `core.` prefix is removed, adapter/bootstrap paths change)
- `.importlinter` configuration must be rewritten for new layer names
- `entrypoint.py` must import from `bootstrap/` instead of `api/` and `scheduler/`
- Test directory structure should mirror the new source layout
- Architecture guard tests must be updated

## Not in Scope

- Restructuring `application/` internals (domain/port/service organization stays the same)
- Changing `base/` internals
- Adding new features or changing business logic
