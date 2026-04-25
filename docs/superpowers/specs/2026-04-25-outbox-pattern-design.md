# Outbox Pattern Design Specification

**Date:** 2026-04-25
**Scope:** table-maintenance backend — replace synchronous event dispatch with transactional outbox

## Goals

1. Persist domain events to an outbox table within the same DB transaction as aggregate state changes
2. Introduce an independent outbox publisher component that polls the outbox and dispatches events asynchronously
3. Decouple event production (services) from event consumption (handlers/consumers)
4. Ensure no events are lost on process crash — outbox table is the source of truth
5. Provide a complete audit trail of all domain events

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Message broker | None (in-process for now) | Single bounded context; broker abstraction ready for future swap |
| Serialization format | JSON (`TEXT` column) | SQLite compatible; PostgreSQL can upgrade to `JSONB` later |
| Outbox publisher deployment | Independent `ROLE=outbox-publisher` | Clean separation of concerns, independently scalable |
| API response for trigger | `202 Accepted` | JobRun is created asynchronously by consumer |
| Processed events | Soft delete (`published_at` timestamp) | Audit trail; periodic cleanup later |
| Which events go to outbox | All domain events | Uniform write path; no handler = mark published immediately (audit only) |

## Outbox Table Schema

```sql
CREATE TABLE domain_event_outbox (
    id             TEXT PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id   TEXT NOT NULL,
    event_type     TEXT NOT NULL,
    payload        TEXT NOT NULL,
    occurred_at    TIMESTAMP NOT NULL,
    published_at   TIMESTAMP NULL
);

CREATE INDEX ix_outbox_unpublished ON domain_event_outbox (published_at)
    WHERE published_at IS NULL;
```

Defined via SQLAlchemy Core in `core/adapter/outbound/sql/outbox_table.py`, registered in shared `metadata`.

## Domain Model

### OutboxEntry Value Object

```python
# core/application/domain/model/outbox_entry.py
@dataclass(frozen=True)
class OutboxEntry:
    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: str               # JSON string
    occurred_at: datetime
    published_at: datetime | None = None
```

Not an aggregate — a flat, immutable data carrier for the outbox table.

## Ports

### EventOutboxRepo

```python
# core/application/port/outbound/event_outbox_repo.py
class EventOutboxRepo(ABC):
    @abstractmethod
    def save(self, entries: list[OutboxEntry]) -> None:
        """Persist outbox entries within the current transaction."""

    @abstractmethod
    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return up to batch_size unpublished entries, ordered by occurred_at."""

    @abstractmethod
    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at = now for the given entry IDs."""
```

## Event Serializer

```python
# core/application/event_handler/event_serializer.py
class EventSerializer:
    def serialize(self, event: DomainEvent) -> str:
        """Convert domain event to JSON string."""

    def deserialize(self, event_type: str, payload: str) -> DomainEvent:
        """Reconstruct domain event from event_type name + JSON string."""

    def to_outbox_entries(
        self,
        events: list[DomainEvent],
        aggregate_type: str,
        aggregate_id: str,
    ) -> list[OutboxEntry]:
        """Convert a list of domain events to outbox entries."""
```

Serialization strategy:
- Domain types (`JobId`, `TriggerType`, etc.) are serialized to their `.value` string representation
- `event_type` is the class name (e.g., `"JobTriggered"`)
- Deserialization uses a registry mapping `event_type` string → event class

## Application Service Changes

### Uniform pattern (all services)

```python
# Before
job.trigger(active_run_count=active_count)
self._dispatcher.dispatch_all(job.collect_events())

# After
job.trigger(active_run_count=active_count)
entries = self._serializer.to_outbox_entries(
    events=job.collect_events(),
    aggregate_type="Job",
    aggregate_id=job.id.value,
)
self._outbox_repo.save(entries)
```

Services no longer depend on `EventDispatcher`. They depend on `EventOutboxRepo` + `EventSerializer`.

### Affected services

| Service | Change |
|---------|--------|
| `CreateJobService` | Replace `EventDispatcher` with `EventOutboxRepo` + `EventSerializer` |
| `UpdateJobService` | Same |
| `CreateJobRunService` | Remove `triggered_handler`, no longer synchronously creates JobRun. Return `TriggerJobOutput(job_id)`. Write `JobTriggered` to outbox. |
| `ScheduleJobsService` | Remove `EventDispatcher`, write to outbox instead |

### CreateJobRunService return type change

```python
# New output
@dataclass(frozen=True)
class TriggerJobOutput:
    job_id: str
    accepted: bool = True
```

API endpoint changes from `201 Created` to `202 Accepted`.

## Outbox Publisher

### OutboxPublisherService

```python
# core/application/service/outbox_publisher.py
class OutboxPublisherService:
    def __init__(
        self,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
        dispatcher: EventDispatcher,
    ) -> None: ...

    def execute(self) -> OutboxPublishResult:
        entries = self._outbox_repo.fetch_unpublished(batch_size=100)
        published: list[str] = []

        for entry in entries:
            event = self._serializer.deserialize(entry.event_type, entry.payload)
            self._dispatcher.dispatch(event)
            published.append(entry.id)

        self._outbox_repo.mark_published(published)
        return OutboxPublishResult(published_count=len(published))
```

Events with no registered handler are dispatched (no-op) and marked published — serving as audit trail only.

### PublisherLoop

```python
# outbox_publisher/publisher_loop.py
class PublisherLoop:
    def __init__(self, service: OutboxPublisherService, interval_seconds: int = 5): ...
    def tick(self) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

Same pattern as existing `SchedulerLoop`.

### Entry Point

```python
# outbox_publisher/main.py
def build_publisher() -> PublisherLoop: ...
def main() -> None: ...
```

`entrypoint.py` adds `ROLE=outbox-publisher` case.

## Consumer (renamed from Handler)

`JobTriggeredHandler` is renamed to `CreateJobRunConsumer`. Logic unchanged: receives `JobTriggered` → creates PENDING `JobRun` → persists.

The consumer's own events (`JobRunCreated`) are also written to the outbox, not synchronously dispatched. This creates an event chain:

```
JobTriggered → CreateJobRunConsumer → writes JobRunCreated to outbox
JobRunCreated → (future) SparkAppSubmitter → writes JobRunStarted to outbox
```

### Currently registered consumers

| Event | Consumer | Action |
|-------|----------|--------|
| `JobTriggered` | `CreateJobRunConsumer` | Create PENDING JobRun, write JobRunCreated to outbox |
| All other events | None | Marked published (audit trail) |

## Data Flow

```
API / Scheduler
  │
  ▼
┌─ Transaction 1 ────────────────────────┐
│  job.trigger() / job.pause() / etc.     │
│  persist aggregate state                │
│  serialize events → write to outbox     │
│  commit                                 │
└─────────────────────────────────────────┘
  │
  ▼ (polling, ~5 seconds)
┌─ Outbox Publisher ──────────────────────┐
│  fetch unpublished entries              │
│  deserialize → dispatch to consumers    │
│  consumer processes event               │
│  mark entries as published              │
└─────────────────────────────────────────┘
```

Each consumer runs in its own transaction. If a consumer fails, the entry stays unpublished and will be retried on the next tick.

## Directory Structure

### New files

```
core/
├── application/
│   ├── domain/model/
│   │   └── outbox_entry.py
│   ├── port/outbound/
│   │   └── event_outbox_repo.py
│   ├── event_handler/
│   │   ├── event_serializer.py
│   │   ├── create_job_run_consumer.py   # renamed from job_triggered_handler.py
│   │   └── (job_triggered_handler.py deleted)
│   └── service/
│       ├── outbox_publisher.py
│       └── outbox_publish_result.py
├── adapter/outbound/
│   └── sql/
│       ├── outbox_table.py
│       └── event_outbox_sql_repo.py
│
outbox_publisher/
├── __init__.py
├── main.py
└── publisher_loop.py
```

### Modified files

| File | Change |
|------|--------|
| `entrypoint.py` | Add `ROLE=outbox-publisher` |
| `core/application/service/job/create_job.py` | `EventDispatcher` → `EventOutboxRepo` + `EventSerializer` |
| `core/application/service/job/update_job.py` | Same |
| `core/application/service/job_run/create_job_run.py` | Remove sync handler, return `TriggerJobOutput`, write outbox |
| `core/application/service/schedule_jobs.py` | Same pattern |
| `api/adapter/inbound/web/job_run/create_job_run.py` | 201 → 202, adjust response |
| `api/dependencies/use_cases.py` | Replace `EventDispatcher` DI with `EventOutboxRepo` + `EventSerializer` |
| `api/dependencies/event_dispatcher.py` | Delete (dispatcher no longer used by API) |
| `core/adapter/outbound/sql/metadata.py` | Register outbox table |
| `.importlinter` | Add outbox_publisher isolation rules |

### Deleted files

| File | Reason |
|------|--------|
| `core/application/event_handler/job_triggered_handler.py` | Renamed to `create_job_run_consumer.py` |
| `api/dependencies/event_dispatcher.py` | Dispatcher no longer used by API layer |

## Architecture Boundaries

```
api (ROLE=api)                  → services → outbox_repo.save()
scheduler (ROLE=scheduler)      → services → outbox_repo.save()
outbox_publisher (ROLE=outbox-publisher) → outbox_repo.fetch() → EventDispatcher → consumers
```

Import-linter rules:
- `outbox_publisher` does not depend on `api`
- `outbox_publisher` does not depend on `scheduler`
- `api` does not depend on `outbox_publisher`
- `scheduler` does not depend on `outbox_publisher`

## Error Handling

- **Service write fails:** Transaction rolls back, aggregate state + outbox entries both reverted. No event lost.
- **Consumer fails:** Entry stays unpublished. Next publisher tick retries. Idempotency is the consumer's responsibility.
- **Publisher crashes:** Unpublished entries remain in outbox. Next startup resumes from where it left off.

## Future Extensions

- **Real message broker:** Replace in-process `EventDispatcher` in publisher with broker adapter (NATS, SQS, etc.)
- **SparkApp submission:** Register `SparkAppSubmitter` consumer for `JobRunCreated` events
- **Cross-bounded-context:** Integration Events with primitive-type serialization for external consumers
- **Outbox cleanup:** Scheduled job to delete old published entries
