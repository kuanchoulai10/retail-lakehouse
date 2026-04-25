# Domain Events Design Specification

**Date:** 2026-04-25
**Scope:** table-maintenance backend — Job & JobRun aggregates

## Goals

1. Decouple aggregate coordination — replace `Job.trigger()` directly constructing `JobRun` with a `JobTriggered` domain event handled by an event handler
2. Record domain facts at every state transition for future event-driven architecture
3. Establish event handler infrastructure (EventDispatcher, EventHandler ABC) for growing complexity

## Event Catalog

### Job Aggregate Events (`domain/model/job/events.py`)

| Event | Trigger | Fields |
|-------|---------|--------|
| `JobCreated` | `Job.create()` factory method | `job_id: JobId`, `job_type: JobType`, `table_ref: TableReference`, `cron: CronExpression \| None` |
| `JobUpdated` | `job.apply_changes()` | `job_id: JobId`, `changes: tuple[FieldChange, ...]` |
| `JobPaused` | `job.pause()` | `job_id: JobId` |
| `JobResumed` | `job.resume()` | `job_id: JobId` |
| `JobArchived` | `job.archive()` | `job_id: JobId` |
| `JobTriggered` | `job.trigger()` | `job_id: JobId`, `trigger_type: TriggerType` |

### JobRun Aggregate Events (`domain/model/job_run/events.py`)

| Event | Trigger | Fields |
|-------|---------|--------|
| `JobRunCreated` | `JobRun.create()` factory method | `run_id: JobRunId`, `job_id: JobId`, `trigger_type: TriggerType` |
| `JobRunStarted` | `run.mark_running()` | `run_id: JobRunId`, `job_id: JobId`, `started_at: datetime` |
| `JobRunCompleted` | `run.mark_completed()` | `run_id: JobRunId`, `job_id: JobId`, `finished_at: datetime` |
| `JobRunFailed` | `run.mark_failed()` | `run_id: JobRunId`, `job_id: JobId`, `finished_at: datetime` |
| `JobRunCancelled` | `run.cancel()` | `run_id: JobRunId`, `job_id: JobId` |

### Supporting Value Object

```python
# domain/model/job/field_change.py
@dataclass(frozen=True)
class FieldChange(ValueObject):
    field: str
    old_value: str | None
    new_value: str | None
```

### Design Decisions — Event Fields

- All events use domain types (`JobId`, `JobRunId`, `TriggerType`, `TableReference`, etc.), not raw primitives. Domain events are consumed within the bounded context.
- If cross-bounded-context publishing is needed in the future, introduce Integration Events that map domain types to primitives for serialization.
- `JobUpdated.changes` uses `tuple` (not `list`) because `frozen=True` dataclasses require hashable fields.
- All events inherit from `DomainEvent` base class, which provides `occurred_at: datetime` automatically.

## Aggregate Behavior Changes

### Job Aggregate

**New `Job.create()` class method (factory):**

```python
@classmethod
def create(cls, id: JobId, job_type: JobType, ...) -> Job:
    job = cls(id=id, job_type=job_type, ...)
    job.register_event(JobCreated(job_id=id, ...))
    return job
```

- `CreateJobService` calls `Job.create()` instead of `Job(...)` directly.
- The aggregate owns its creation event, not the application service.

**`trigger()` no longer returns JobRun:**

```python
def trigger(self, active_run_count: int, trigger_type: TriggerType = TriggerType.MANUAL) -> None:
    if not self.is_active:
        raise JobNotActiveError(self.id.value)
    if active_run_count >= self.max_active_runs:
        raise MaxActiveRunsExceededError(self.id.value, self.max_active_runs)
    self.register_event(JobTriggered(job_id=self.id, trigger_type=trigger_type))
```

- Invariant guards remain on the aggregate.
- JobRun construction moves to `JobTriggeredHandler`.

**State transition methods register events:**

```python
def pause(self) -> None:
    self._transition_to(JobStatus.PAUSED)
    self.register_event(JobPaused(job_id=self.id))
```

Same pattern for `resume()` and `archive()`.

**New `job.apply_changes()` for configuration updates:**

```python
def apply_changes(
    self,
    table_ref: TableReference | None = None,
    cron: CronExpression | None = None,
    job_config: dict | None = None,
) -> None:
    changes: list[FieldChange] = []
    if table_ref is not None and table_ref != self.table_ref:
        changes.append(FieldChange(field="table_ref", old_value=str(self.table_ref), new_value=str(table_ref)))
        self.table_ref = table_ref
    if cron is not None and cron != self.cron:
        changes.append(FieldChange(field="cron", old_value=str(self.cron), new_value=str(cron)))
        self.cron = cron
    if job_config is not None and job_config != self.job_config:
        changes.append(FieldChange(field="job_config", old_value=str(self.job_config), new_value=str(job_config)))
        self.job_config = job_config
    if changes:
        self.register_event(JobUpdated(job_id=self.id, changes=tuple(changes)))
```

- `UpdateJobService` calls `job.apply_changes(...)` instead of mutating fields directly.
- The aggregate owns the comparison logic and event registration.
- Status changes (`pause`/`resume`/`archive`) remain as separate methods with their own events.

**Remove `DeleteJobService`.** `archive()` + `JobArchived` serves as the domain-driven end-of-life. Hard delete is not a domain concept.

### JobRun Aggregate

**New `JobRun.create()` class method (factory):**

```python
@classmethod
def create(cls, id: JobRunId, job_id: JobId, trigger_type: TriggerType, started_at: datetime) -> JobRun:
    run = cls(id=id, job_id=job_id, status=JobRunStatus.PENDING, trigger_type=trigger_type, started_at=started_at)
    run.register_event(JobRunCreated(run_id=id, job_id=job_id, trigger_type=trigger_type))
    return run
```

**State transition methods register events:**

```python
def mark_running(self, started_at: datetime) -> None:
    self._transition_to(JobRunStatus.RUNNING)
    self.started_at = started_at
    self.register_event(JobRunStarted(run_id=self.id, job_id=self.job_id, started_at=started_at))
```

Same pattern for `mark_completed()`, `mark_failed()`, `cancel()`.

## Event Handler Infrastructure

### Directory Structure

```
core/application/
├── event_handler/
│   ├── __init__.py
│   ├── event_handler.py          # EventHandler ABC
│   ├── event_dispatcher.py       # EventDispatcher
│   └── job_triggered_handler.py  # First concrete handler
├── service/                      # Existing use cases
├── port/                         # Existing ports
└── domain/model/
    ├── job/events.py             # Job domain events
    └── job_run/events.py         # JobRun domain events
```

### EventHandler ABC

```python
# application/event_handler/event_handler.py
class EventHandler(ABC, Generic[E]):
    @abstractmethod
    def handle(self, event: E) -> None: ...
```

### EventDispatcher

```python
# application/event_handler/event_dispatcher.py
class EventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def register(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler.handle(event)

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.dispatch(event)
```

### JobTriggeredHandler

```python
# application/event_handler/job_triggered_handler.py
class JobTriggeredHandler(EventHandler[JobTriggered]):
    def __init__(self, job_runs_repo: JobRunsRepo) -> None:
        self._job_runs_repo = job_runs_repo

    def handle(self, event: JobTriggered) -> None:
        run = JobRun.create(
            id=JobRunId(value=f"{event.job_id.value}-{secrets.token_hex(3)}"),
            job_id=event.job_id,
            trigger_type=event.trigger_type,
            started_at=datetime.now(UTC),
        )
        self._job_runs_repo.create(run)
```

### Handler Registration (DI layer)

```python
dispatcher = EventDispatcher()
dispatcher.register(JobTriggered, JobTriggeredHandler(job_runs_repo))
```

### Application Service Usage

All services follow a uniform pattern:

```python
def execute(self, request: ...):
    # 1. Load aggregate
    # 2. Call aggregate behavior
    # 3. Persist aggregate
    # 4. Dispatch events
    self._dispatcher.dispatch_all(aggregate.collect_events())
```

## Transactional Consistency

**Current approach:** Synchronous, in-process transactional consistency.

- Application service: persist aggregate + collect events + call handlers — all within the same DB transaction.
- If persist fails: exception propagates, events are never collected.
- If handler fails: transaction rolls back, aggregate state is reverted.

**Future migration path:** When cross-bounded-context communication is needed, introduce the Outbox Pattern — domain events are written to a `domain_events` table within the same transaction, then published to a message broker by a background worker.

## Migration Notes

- `DeleteJobService` is removed. All existing delete API endpoints should be remapped to call `archive()` via `UpdateJobService`.
- `Job.trigger()` return type changes from `JobRun` to `None`. All callers (`CreateJobRunService`, `ScheduleJobsService`) must be updated to use the event-driven flow.
- `Job(...)` direct construction in services is replaced by `Job.create(...)`.
- `JobRun(...)` direct construction is replaced by `JobRun.create(...)`.
