# Outbound Port & Adapter Naming Convention

## Overview

Define a bounded, consistent naming system for all outbound ports and their adapter implementations. Every outbound port must inherit from one of three base classes, each with a fixed naming pattern. This eliminates ad-hoc naming decisions during development.

## Three Outbound Port Base Classes

All outbound ports must inherit from exactly one of these base classes (defined in `base/`):

| Base Class | Definition | Judgment Criteria |
|------------|-----------|-------------------|
| `Repository` | Aggregate persistence | Manages the lifecycle of a domain aggregate within your own bounded context |
| `Store` | Infrastructure persistence | CRUD against the database, but the target is NOT a domain aggregate |
| `Gateway` | External system interaction | Crosses a system boundary — read, write, trigger, poll an external system |

`Repository` already exists in `base/repository.py`. `Store` and `Gateway` are new marker ABCs with no abstract methods.

```python
# base/store.py
class Store(ABC):
    """Infrastructure persistence that is not an aggregate repository."""

# base/gateway.py
class Gateway(ABC):
    """Port for interacting with external systems."""
```

## Port Naming Rules

| Base Class | Format | Examples |
|------------|--------|----------|
| `Repository` | `{Aggregate}Repo` | `JobsRepo`, `JobRunsRepo` |
| `Store` | `{Noun}Store` | `EventOutboxStore` |
| `Gateway` | `{Verb}{Noun}Gateway` | `ReadCatalogGateway`, `SubmitJobRunGateway` |

### Gateway Verb Vocabulary

Gateway names must use one of these approved verbs. Adding a new verb requires review.

| Verb | Semantics |
|------|-----------|
| `Read` | Read-only query from an external system |
| `Submit` | Trigger an external system to execute an action |
| `Send` | Push a message or notification to an external target |
| `Publish` | Emit events to a message broker |
| `Poll` | Actively poll an external system for status updates |
| `Sync` | Bidirectional data synchronization |
| `Write` | Write data to an external system (not your own DB) |
| `Delete` | Remove or revoke a resource in an external system |

## Adapter Naming Rules

Format: insert the technology name before the base class suffix.

| Base Class | Port | Adapter Format | Examples |
|------------|------|---------------|----------|
| `Repository` | `{Aggregate}Repo` | `{Aggregate}{Tech}Repo` | `JobsSqlRepo`, `JobsInMemoryRepo` |
| `Store` | `{Noun}Store` | `{Noun}{Tech}Store` | `EventOutboxSqlStore`, `EventOutboxInMemoryStore` |
| `Gateway` | `{Verb}{Noun}Gateway` | `{Verb}{Noun}{Tech}Gateway` | `ReadCatalogIcebergGateway`, `SubmitJobRunK8sGateway` |

Common `{Tech}` values: `Sql`, `InMemory`, `K8s`, `Iceberg`, `Http`, `Grpc`.

## File Naming Rules

Class name converted to snake_case becomes the filename. One class per file.

| Class | File |
|-------|------|
| `JobsRepo` | `jobs_repo.py` |
| `EventOutboxStore` | `event_outbox_store.py` |
| `SubmitJobRunGateway` | `submit_job_run_gateway.py` |
| `SubmitJobRunK8sGateway` | `submit_job_run_k8s_gateway.py` |

## Directory Structure

### Port (application layer)

```
application/port/outbound/
├── job/
│   └── jobs_repo.py                  # JobsRepo(Repository[Job])
├── job_run/
│   ├── job_runs_repo.py              # JobRunsRepo(Repository[JobRun])
│   ├── submit_job_run_gateway.py     # SubmitJobRunGateway(Gateway)
│   └── job_submission.py             # JobSubmission (Gateway input VO)
├── catalog/
│   └── read_catalog_gateway.py       # ReadCatalogGateway(Gateway)
└── event_outbox/
    └── event_outbox_store.py         # EventOutboxStore(Store)
```

### Adapter (adapter layer)

```
adapter/outbound/
├── job/
│   ├── sql/
│   │   └── jobs_sql_repo.py                    # JobsSqlRepo
│   └── jobs_in_memory_repo.py                   # JobsInMemoryRepo
├── job_run/
│   ├── sql/
│   │   └── job_runs_sql_repo.py                 # JobRunsSqlRepo
│   ├── k8s/
│   │   └── submit_job_run_k8s_gateway.py        # SubmitJobRunK8sGateway
│   ├── job_runs_in_memory_repo.py               # JobRunsInMemoryRepo
│   └── submit_job_run_in_memory_gateway.py      # SubmitJobRunInMemoryGateway
├── catalog/
│   └── read_catalog_iceberg_gateway.py          # ReadCatalogIcebergGateway
└── sql/
    ├── event_outbox_sql_store.py                # EventOutboxSqlStore
    ├── engine_factory.py
    └── metadata.py
```

## Migration: Current → New

| Current | New |
|---------|-----|
| `JobsRepo` | `JobsRepo` (no change) |
| `JobRunsRepo` | `JobRunsRepo` (no change) |
| `EventOutboxRepo` | `EventOutboxStore` |
| `CatalogReader` | `ReadCatalogGateway` |
| `JobRunExecutor` | `SubmitJobRunGateway` |
| `JobSubmission` | `JobSubmission` (no change, VO) |
| `JobsSqlRepo` | `JobsSqlRepo` (no change) |
| `JobsInMemoryRepo` | `JobsInMemoryRepo` (no change) |
| `JobRunsSqlRepo` | `JobRunsSqlRepo` (no change) |
| `JobRunsInMemoryRepo` | `JobRunsInMemoryRepo` (no change) |
| `EventOutboxSqlRepo` | `EventOutboxSqlStore` |
| `IcebergCatalogClient` | `ReadCatalogIcebergGateway` |
| `JobRunK8sExecutor` | `SubmitJobRunK8sGateway` |
| `JobRunInMemoryExecutor` | `SubmitJobRunInMemoryGateway` |
