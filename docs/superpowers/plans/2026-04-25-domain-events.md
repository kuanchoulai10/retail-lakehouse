# Domain Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add domain events to Job and JobRun aggregates, establish EventDispatcher/EventHandler infrastructure, and decouple Job→JobRun creation via the `JobTriggered` event.

**Architecture:** Domain events are defined in each aggregate's model package. A new `event_handler/` layer in `core/application/` provides an `EventHandler` ABC and `EventDispatcher`. Application services dispatch events after persisting aggregates. `JobTriggeredHandler` replaces direct `JobRun` construction inside `Job.trigger()`.

**Tech Stack:** Python dataclasses, `core.base.DomainEvent`, `core.base.ValueObject`, `core.base.AggregateRoot`

**Spec:** `docs/superpowers/specs/2026-04-25-domain-events-design.md`

**Shorthand:** `B = src/table-maintenance/backend`, `T = src/table-maintenance/backend/tests`

**Run commands prefix:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend`

---

### Task 1: FieldChange Value Object

**Files:**
- Create: `B/core/application/domain/model/job/field_change.py`
- Test: `T/application/domain/model/job/test_field_change.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/domain/model/job/test_field_change.py
"""Tests for FieldChange value object."""

from core.base import ValueObject
from core.application.domain.model.job.field_change import FieldChange


def test_is_value_object():
    """Verify FieldChange is a ValueObject subclass."""
    assert issubclass(FieldChange, ValueObject)


def test_fields():
    """Verify FieldChange stores field, old_value, new_value."""
    fc = FieldChange(field="cron", old_value="0 * * * *", new_value="0 2 * * *")
    assert fc.field == "cron"
    assert fc.old_value == "0 * * * *"
    assert fc.new_value == "0 2 * * *"


def test_frozen():
    """Verify FieldChange is immutable."""
    import pytest

    fc = FieldChange(field="cron", old_value=None, new_value="0 2 * * *")
    with pytest.raises(AttributeError):
        fc.field = "other"


def test_equality_by_value():
    """Verify two FieldChanges with same values are equal."""
    a = FieldChange(field="cron", old_value=None, new_value="0 2 * * *")
    b = FieldChange(field="cron", old_value=None, new_value="0 2 * * *")
    assert a == b


def test_none_values_allowed():
    """Verify old_value and new_value can be None."""
    fc = FieldChange(field="cron", old_value=None, new_value=None)
    assert fc.old_value is None
    assert fc.new_value is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_field_change.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.application.domain.model.job.field_change'`

- [ ] **Step 3: Write minimal implementation**

```python
# B/core/application/domain/model/job/field_change.py
"""Define the FieldChange value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class FieldChange(ValueObject):
    """A record of a single field change with before/after values."""

    field: str
    old_value: str | None
    new_value: str | None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_field_change.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Add to package `__init__.py`**

Add `FieldChange` to `B/core/application/domain/model/job/__init__.py`:

```python
from core.application.domain.model.job.field_change import FieldChange
```

And add `"FieldChange"` to the `__all__` list.

- [ ] **Step 6: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job/field_change.py \
        src/table-maintenance/backend/core/application/domain/model/job/__init__.py \
        src/table-maintenance/backend/tests/application/domain/model/job/test_field_change.py
git commit -m "feat(domain): add FieldChange value object"
```

---

### Task 2: Job Domain Events

**Files:**
- Create: `B/core/application/domain/model/job/events.py`
- Test: `T/application/domain/model/job/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/domain/model/job/test_events.py
"""Tests for Job domain events."""

from datetime import UTC, datetime

from core.base import DomainEvent
from core.application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    TableReference,
)
from core.application.domain.model.job.field_change import FieldChange
from core.application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from core.application.domain.model.job_run import TriggerType


class TestJobCreated:
    """Tests for JobCreated event."""

    def test_is_domain_event(self):
        assert issubclass(JobCreated, DomainEvent)

    def test_fields(self):
        ev = JobCreated(
            job_id=JobId(value="j1"),
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            cron=CronExpression(expression="0 * * * *"),
        )
        assert ev.job_id == JobId(value="j1")
        assert ev.job_type == JobType.EXPIRE_SNAPSHOTS
        assert ev.table_ref == TableReference(catalog="cat", table="tbl")
        assert ev.cron == CronExpression(expression="0 * * * *")

    def test_cron_none(self):
        ev = JobCreated(
            job_id=JobId(value="j1"),
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            cron=None,
        )
        assert ev.cron is None

    def test_has_occurred_at(self):
        ev = JobCreated(
            job_id=JobId(value="j1"),
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            cron=None,
        )
        assert isinstance(ev.occurred_at, datetime)

    def test_frozen(self):
        import pytest

        ev = JobCreated(
            job_id=JobId(value="j1"),
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            cron=None,
        )
        with pytest.raises(AttributeError):
            ev.job_id = JobId(value="j2")


class TestJobUpdated:
    """Tests for JobUpdated event."""

    def test_fields(self):
        changes = (
            FieldChange(field="cron", old_value="0 * * * *", new_value="0 2 * * *"),
        )
        ev = JobUpdated(job_id=JobId(value="j1"), changes=changes)
        assert ev.job_id == JobId(value="j1")
        assert len(ev.changes) == 1
        assert ev.changes[0].field == "cron"

    def test_changes_is_tuple(self):
        ev = JobUpdated(job_id=JobId(value="j1"), changes=())
        assert isinstance(ev.changes, tuple)


class TestJobPaused:
    """Tests for JobPaused event."""

    def test_fields(self):
        ev = JobPaused(job_id=JobId(value="j1"))
        assert ev.job_id == JobId(value="j1")
        assert isinstance(ev.occurred_at, datetime)


class TestJobResumed:
    """Tests for JobResumed event."""

    def test_fields(self):
        ev = JobResumed(job_id=JobId(value="j1"))
        assert ev.job_id == JobId(value="j1")


class TestJobArchived:
    """Tests for JobArchived event."""

    def test_fields(self):
        ev = JobArchived(job_id=JobId(value="j1"))
        assert ev.job_id == JobId(value="j1")


class TestJobTriggered:
    """Tests for JobTriggered event."""

    def test_fields(self):
        ev = JobTriggered(
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
        )
        assert ev.job_id == JobId(value="j1")
        assert ev.trigger_type == TriggerType.MANUAL

    def test_scheduled(self):
        ev = JobTriggered(
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.SCHEDULED,
        )
        assert ev.trigger_type == TriggerType.SCHEDULED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.application.domain.model.job.events'`

- [ ] **Step 3: Write minimal implementation**

```python
# B/core/application/domain/model/job/events.py
"""Define domain events for the Job aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.domain_event import DomainEvent

if TYPE_CHECKING:
    from core.application.domain.model.job.cron_expression import CronExpression
    from core.application.domain.model.job.field_change import FieldChange
    from core.application.domain.model.job.job_id import JobId
    from core.application.domain.model.job.job_type import JobType
    from core.application.domain.model.job.table_reference import TableReference
    from core.application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobCreated(DomainEvent):
    """Raised when a new Job is created via the factory method."""

    job_id: JobId
    job_type: JobType
    table_ref: TableReference
    cron: CronExpression | None


@dataclass(frozen=True)
class JobUpdated(DomainEvent):
    """Raised when Job configuration fields are changed."""

    job_id: JobId
    changes: tuple[FieldChange, ...]


@dataclass(frozen=True)
class JobPaused(DomainEvent):
    """Raised when a Job transitions from ACTIVE to PAUSED."""

    job_id: JobId


@dataclass(frozen=True)
class JobResumed(DomainEvent):
    """Raised when a Job transitions from PAUSED to ACTIVE."""

    job_id: JobId


@dataclass(frozen=True)
class JobArchived(DomainEvent):
    """Raised when a Job transitions to ARCHIVED (end-of-life)."""

    job_id: JobId


@dataclass(frozen=True)
class JobTriggered(DomainEvent):
    """Raised when a Job is triggered to create a new run."""

    job_id: JobId
    trigger_type: TriggerType
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_events.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job/events.py \
        src/table-maintenance/backend/tests/application/domain/model/job/test_events.py
git commit -m "feat(domain): add Job aggregate domain events"
```

---

### Task 3: JobRun Domain Events

**Files:**
- Create: `B/core/application/domain/model/job_run/events.py`
- Test: `T/application/domain/model/job_run/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/domain/model/job_run/test_events.py
"""Tests for JobRun domain events."""

from datetime import UTC, datetime

from core.base import DomainEvent
from core.application.domain.model.job import JobId
from core.application.domain.model.job_run import JobRunId, TriggerType
from core.application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)


class TestJobRunCreated:
    """Tests for JobRunCreated event."""

    def test_is_domain_event(self):
        assert issubclass(JobRunCreated, DomainEvent)

    def test_fields(self):
        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
        )
        assert ev.run_id == JobRunId(value="r1")
        assert ev.job_id == JobId(value="j1")
        assert ev.trigger_type == TriggerType.MANUAL

    def test_has_occurred_at(self):
        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.SCHEDULED,
        )
        assert isinstance(ev.occurred_at, datetime)

    def test_frozen(self):
        import pytest

        ev = JobRunCreated(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
        )
        with pytest.raises(AttributeError):
            ev.run_id = JobRunId(value="r2")


class TestJobRunStarted:
    """Tests for JobRunStarted event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
        ev = JobRunStarted(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            started_at=ts,
        )
        assert ev.started_at == ts


class TestJobRunCompleted:
    """Tests for JobRunCompleted event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 13, 0, tzinfo=UTC)
        ev = JobRunCompleted(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            finished_at=ts,
        )
        assert ev.finished_at == ts


class TestJobRunFailed:
    """Tests for JobRunFailed event."""

    def test_fields(self):
        ts = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        ev = JobRunFailed(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
            finished_at=ts,
        )
        assert ev.finished_at == ts


class TestJobRunCancelled:
    """Tests for JobRunCancelled event."""

    def test_fields(self):
        ev = JobRunCancelled(
            run_id=JobRunId(value="r1"),
            job_id=JobId(value="j1"),
        )
        assert ev.run_id == JobRunId(value="r1")
        assert ev.job_id == JobId(value="j1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# B/core/application/domain/model/job_run/events.py
"""Define domain events for the JobRun aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.domain_event import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job.job_id import JobId
    from core.application.domain.model.job_run.job_run_id import JobRunId
    from core.application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobRunCreated(DomainEvent):
    """Raised when a new JobRun is created via the factory method."""

    run_id: JobRunId
    job_id: JobId
    trigger_type: TriggerType


@dataclass(frozen=True)
class JobRunStarted(DomainEvent):
    """Raised when a JobRun transitions from PENDING to RUNNING."""

    run_id: JobRunId
    job_id: JobId
    started_at: datetime


@dataclass(frozen=True)
class JobRunCompleted(DomainEvent):
    """Raised when a JobRun transitions from RUNNING to COMPLETED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime


@dataclass(frozen=True)
class JobRunFailed(DomainEvent):
    """Raised when a JobRun transitions to FAILED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime


@dataclass(frozen=True)
class JobRunCancelled(DomainEvent):
    """Raised when a JobRun is cancelled."""

    run_id: JobRunId
    job_id: JobId
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_events.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job_run/events.py \
        src/table-maintenance/backend/tests/application/domain/model/job_run/test_events.py
git commit -m "feat(domain): add JobRun aggregate domain events"
```

---

### Task 4: EventHandler ABC and EventDispatcher

**Files:**
- Create: `B/core/application/event_handler/__init__.py`
- Create: `B/core/application/event_handler/event_handler.py`
- Create: `B/core/application/event_handler/event_dispatcher.py`
- Test: `T/application/event_handler/__init__.py`
- Test: `T/application/event_handler/test_event_handler.py`
- Test: `T/application/event_handler/test_event_dispatcher.py`

- [ ] **Step 1: Write failing test for EventHandler**

```python
# T/application/event_handler/__init__.py
```

```python
# T/application/event_handler/test_event_handler.py
"""Tests for EventHandler ABC."""

from dataclasses import dataclass

import pytest

from core.base import DomainEvent
from core.application.event_handler.event_handler import EventHandler


@dataclass(frozen=True)
class _StubEvent(DomainEvent):
    value: str


def test_is_abstract():
    """Verify EventHandler cannot be instantiated directly."""
    with pytest.raises(TypeError):
        EventHandler()


def test_concrete_handler_can_handle():
    """Verify a concrete EventHandler subclass can handle events."""
    handled: list[_StubEvent] = []

    class _StubHandler(EventHandler[_StubEvent]):
        def handle(self, event: _StubEvent) -> None:
            handled.append(event)

    handler = _StubHandler()
    ev = _StubEvent(value="hello")
    handler.handle(ev)
    assert handled == [ev]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_event_handler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write EventHandler implementation**

```python
# B/core/application/event_handler/__init__.py
"""Event handler infrastructure."""
```

```python
# B/core/application/event_handler/event_handler.py
"""Define the EventHandler abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from core.base.domain_event import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class EventHandler(ABC, Generic[E]):
    """Abstract handler for a specific domain event type."""

    @abstractmethod
    def handle(self, event: E) -> None:
        """Process the given domain event."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_event_handler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Write failing test for EventDispatcher**

```python
# T/application/event_handler/test_event_dispatcher.py
"""Tests for EventDispatcher."""

from dataclasses import dataclass

from core.base import DomainEvent
from core.application.event_handler.event_dispatcher import EventDispatcher
from core.application.event_handler.event_handler import EventHandler


@dataclass(frozen=True)
class _EventA(DomainEvent):
    value: str


@dataclass(frozen=True)
class _EventB(DomainEvent):
    value: int


class _RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class TestDispatch:
    """Tests for EventDispatcher.dispatch()."""

    def test_dispatch_to_registered_handler(self):
        """Verify event is dispatched to the correct handler."""
        dispatcher = EventDispatcher()
        handler = _RecordingHandler()
        dispatcher.register(_EventA, handler)
        ev = _EventA(value="hello")
        dispatcher.dispatch(ev)
        assert handler.events == [ev]

    def test_dispatch_ignores_unregistered_event(self):
        """Verify unregistered event types are silently ignored."""
        dispatcher = EventDispatcher()
        handler = _RecordingHandler()
        dispatcher.register(_EventA, handler)
        dispatcher.dispatch(_EventB(value=42))
        assert handler.events == []

    def test_dispatch_to_multiple_handlers(self):
        """Verify event is dispatched to all registered handlers for that type."""
        dispatcher = EventDispatcher()
        h1 = _RecordingHandler()
        h2 = _RecordingHandler()
        dispatcher.register(_EventA, h1)
        dispatcher.register(_EventA, h2)
        ev = _EventA(value="hello")
        dispatcher.dispatch(ev)
        assert h1.events == [ev]
        assert h2.events == [ev]


class TestDispatchAll:
    """Tests for EventDispatcher.dispatch_all()."""

    def test_dispatch_all_routes_each_event(self):
        """Verify dispatch_all routes each event to its handler."""
        dispatcher = EventDispatcher()
        ha = _RecordingHandler()
        hb = _RecordingHandler()
        dispatcher.register(_EventA, ha)
        dispatcher.register(_EventB, hb)
        ea = _EventA(value="a")
        eb = _EventB(value=1)
        dispatcher.dispatch_all([ea, eb])
        assert ha.events == [ea]
        assert hb.events == [eb]

    def test_dispatch_all_empty_list(self):
        """Verify dispatch_all with empty list does nothing."""
        dispatcher = EventDispatcher()
        dispatcher.dispatch_all([])
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_event_dispatcher.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 7: Write EventDispatcher implementation**

```python
# B/core/application/event_handler/event_dispatcher.py
"""Define the EventDispatcher for routing domain events to handlers."""

from __future__ import annotations

from core.base.domain_event import DomainEvent
from core.application.event_handler.event_handler import EventHandler


class EventDispatcher:
    """Routes domain events to registered handlers."""

    def __init__(self) -> None:
        """Initialize with an empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def register(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch a single event to all registered handlers for its type."""
        for handler in self._handlers.get(type(event), []):
            handler.handle(event)

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Dispatch a list of events in order."""
        for event in events:
            self.dispatch(event)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add src/table-maintenance/backend/core/application/event_handler/ \
        src/table-maintenance/backend/tests/application/event_handler/
git commit -m "feat(application): add EventHandler ABC and EventDispatcher"
```

---

### Task 5: Job.create() Factory Method + Event Registration on pause/resume/archive

**Files:**
- Modify: `B/core/application/domain/model/job/job.py`
- Modify: `T/application/domain/model/job/test_job.py`
- Modify: `T/application/domain/model/job/test_job_transitions.py`

- [ ] **Step 1: Write failing tests for Job.create() and event registration**

Add to `T/application/domain/model/job/test_job.py`:

```python
# Add these imports at the top
from core.application.domain.model.job.events import JobCreated

# Add this test
def test_create_factory_returns_job_with_event():
    """Verify Job.create() returns a Job and registers a JobCreated event."""
    job = Job.create(
        id=JobId(value="j1"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="orders"),
        cron=CronExpression(expression="0 2 * * *"),
    )
    assert job.id == JobId(value="j1")
    assert job.job_type == JobType.REWRITE_DATA_FILES
    events = job.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobCreated)
    assert events[0].job_id == JobId(value="j1")
    assert events[0].job_type == JobType.REWRITE_DATA_FILES
    assert events[0].table_ref == TableReference(catalog="retail", table="orders")
    assert events[0].cron == CronExpression(expression="0 2 * * *")


def test_create_factory_with_no_cron():
    """Verify Job.create() works with cron=None."""
    job = Job.create(
        id=JobId(value="j1"),
        job_type=JobType.EXPIRE_SNAPSHOTS,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
    )
    events = job.collect_events()
    assert events[0].cron is None
```

Add to `T/application/domain/model/job/test_job_transitions.py`, inside each existing transition test class:

```python
# Add import at top
from core.application.domain.model.job.events import JobArchived, JobPaused, JobResumed

# Add inside TestPause class:
    def test_pause_registers_event(self):
        """Verify pause() registers a JobPaused event."""
        job = _make_job(JobStatus.ACTIVE)
        job.pause()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobPaused)
        assert events[0].job_id == JobId(value="job-1")

# Add inside TestResume class:
    def test_resume_registers_event(self):
        """Verify resume() registers a JobResumed event."""
        job = _make_job(JobStatus.PAUSED)
        job.resume()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobResumed)
        assert events[0].job_id == JobId(value="job-1")

# Add inside TestArchive class:
    def test_archive_registers_event(self):
        """Verify archive() registers a JobArchived event."""
        job = _make_job(JobStatus.ACTIVE)
        job.archive()
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobArchived)
        assert events[0].job_id == JobId(value="job-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_job.py::test_create_factory_returns_job_with_event tests/application/domain/model/job/test_job_transitions.py::TestPause::test_pause_registers_event -v`
Expected: FAIL — `Job` has no `create` method, `pause()` does not register events

- [ ] **Step 3: Update Job aggregate**

Replace the full content of `B/core/application/domain/model/job/job.py`:

```python
"""Define the Job aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.aggregate_root import AggregateRoot

from core.application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
)
from core.application.domain.model.job.exceptions import (
    InvalidJobStateTransitionError,
    JobNotActiveError,
    MaxActiveRunsExceededError,
)
from core.application.domain.model.job.cron_expression import CronExpression
from core.application.domain.model.job.job_id import JobId
from core.application.domain.model.job.job_status import JobStatus
from core.application.domain.model.job.table_reference import TableReference

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job.job_type import JobType
    from core.application.domain.model.job_run.trigger_type import TriggerType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context.

    Execution state lives in the JobRun aggregate, not on the Job.
    """

    id: JobId
    job_type: JobType
    created_at: datetime
    updated_at: datetime
    table_ref: TableReference = TableReference(catalog="", table="")
    job_config: dict | None = None
    cron: CronExpression | None = None
    status: JobStatus = JobStatus.ACTIVE
    next_run_at: datetime | None = None
    max_active_runs: int = 1

    def __post_init__(self) -> None:
        """Initialize job_config to an empty dict if not provided."""
        if self.job_config is None:
            self.job_config = {}

    @classmethod
    def create(
        cls,
        id: JobId,
        job_type: JobType,
        created_at: datetime,
        updated_at: datetime,
        table_ref: TableReference = TableReference(catalog="", table=""),
        job_config: dict | None = None,
        cron: CronExpression | None = None,
        status: JobStatus = JobStatus.ACTIVE,
        next_run_at: datetime | None = None,
        max_active_runs: int = 1,
    ) -> Job:
        """Create a new Job and register a JobCreated event."""
        job = cls(
            id=id,
            job_type=job_type,
            created_at=created_at,
            updated_at=updated_at,
            table_ref=table_ref,
            job_config=job_config,
            cron=cron,
            status=status,
            next_run_at=next_run_at,
            max_active_runs=max_active_runs,
        )
        job.register_event(
            JobCreated(
                job_id=id,
                job_type=job_type,
                table_ref=table_ref,
                cron=cron,
            )
        )
        return job

    @property
    def is_active(self) -> bool:
        """Return True if the job is in ACTIVE status."""
        return self.status == JobStatus.ACTIVE

    def _transition_to(self, target: JobStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidJobStateTransitionError(self.status.value, target.value)
        self.status = target

    def pause(self) -> None:
        """Transition from ACTIVE to PAUSED."""
        self._transition_to(JobStatus.PAUSED)
        self.register_event(JobPaused(job_id=self.id))

    def resume(self) -> None:
        """Transition from PAUSED to ACTIVE."""
        self._transition_to(JobStatus.ACTIVE)
        self.register_event(JobResumed(job_id=self.id))

    def archive(self) -> None:
        """Transition from ACTIVE or PAUSED to ARCHIVED."""
        self._transition_to(JobStatus.ARCHIVED)
        self.register_event(JobArchived(job_id=self.id))

    def trigger(
        self,
        active_run_count: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> None:
        """Guard trigger invariants and register a JobTriggered event.

        Raises:
            JobNotActiveError: if the job is not ACTIVE.
            MaxActiveRunsExceededError: if active_run_count >= max_active_runs.
        """
        if not self.is_active:
            raise JobNotActiveError(self.id.value)
        if active_run_count >= self.max_active_runs:
            raise MaxActiveRunsExceededError(self.id.value, self.max_active_runs)
        self.register_event(
            JobTriggered(job_id=self.id, trigger_type=trigger_type)
        )
```

- [ ] **Step 4: Run all Job model tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/ -v`
Expected: New tests PASS. Existing `TestTrigger` tests FAIL (they still expect `trigger()` to return a `JobRun`) — these will be fixed in the next step.

- [ ] **Step 5: Update TestTrigger tests for new trigger() signature**

Replace the `TestTrigger` class in `T/application/domain/model/job/test_job_transitions.py`:

```python
# Add import at top
from core.application.domain.model.job.events import JobArchived, JobPaused, JobResumed, JobTriggered
from core.application.domain.model.job_run import TriggerType

# Replace class TestTrigger:
class TestTrigger:
    """Tests for Job.trigger()."""

    def test_registers_job_triggered_event(self):
        """Verify trigger registers a JobTriggered event."""
        job = _make_job(JobStatus.ACTIVE)
        job.trigger(active_run_count=0)
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobTriggered)
        assert events[0].job_id == JobId(value="job-1")
        assert events[0].trigger_type == TriggerType.MANUAL

    def test_trigger_with_scheduled_type(self):
        """Verify trigger passes through trigger_type."""
        job = _make_job(JobStatus.ACTIVE)
        job.trigger(active_run_count=0, trigger_type=TriggerType.SCHEDULED)
        events = job.collect_events()
        assert events[0].trigger_type == TriggerType.SCHEDULED

    def test_raises_when_not_active(self):
        """Verify trigger raises JobNotActiveError for paused job."""
        job = _make_job(JobStatus.PAUSED)
        with pytest.raises(JobNotActiveError):
            job.trigger(active_run_count=0)

    def test_raises_when_max_active_runs_exceeded(self):
        """Verify trigger raises MaxActiveRunsExceededError."""
        job = _make_job(JobStatus.ACTIVE)
        job.max_active_runs = 1
        with pytest.raises(MaxActiveRunsExceededError):
            job.trigger(active_run_count=1)

    def test_no_event_on_failure(self):
        """Verify no event is registered when trigger fails."""
        job = _make_job(JobStatus.PAUSED)
        with pytest.raises(JobNotActiveError):
            job.trigger(active_run_count=0)
        assert job.collect_events() == []
```

Also remove the now-unused import `from core.application.domain.model.job_run import JobRunId, JobRunStatus` if it's only used by the old trigger tests. Keep `TriggerType` which is still needed.

- [ ] **Step 6: Run all Job model tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job/job.py \
        src/table-maintenance/backend/tests/application/domain/model/job/test_job.py \
        src/table-maintenance/backend/tests/application/domain/model/job/test_job_transitions.py
git commit -m "feat(domain): add Job.create() factory, register events on state transitions"
```

---

### Task 6: Job.apply_changes() Method

**Files:**
- Modify: `B/core/application/domain/model/job/job.py`
- Test: `T/application/domain/model/job/test_job_transitions.py`

- [ ] **Step 1: Write failing tests**

Add a new test class to `T/application/domain/model/job/test_job_transitions.py`:

```python
# Add imports at top
from core.application.domain.model.job import CronExpression, TableReference
from core.application.domain.model.job.events import JobUpdated
from core.application.domain.model.job.field_change import FieldChange


class TestApplyChanges:
    """Tests for Job.apply_changes()."""

    def test_change_cron(self):
        """Verify changing cron registers JobUpdated with FieldChange."""
        job = _make_job(JobStatus.ACTIVE)
        old_cron = CronExpression(expression="0 * * * *")
        new_cron = CronExpression(expression="0 2 * * *")
        job.cron = old_cron
        job.apply_changes(cron=new_cron)
        assert job.cron == new_cron
        events = job.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobUpdated)
        assert len(events[0].changes) == 1
        assert events[0].changes[0].field == "cron"

    def test_change_table_ref(self):
        """Verify changing table_ref registers JobUpdated."""
        job = _make_job(JobStatus.ACTIVE)
        new_ref = TableReference(catalog="new_cat", table="new_tbl")
        job.apply_changes(table_ref=new_ref)
        assert job.table_ref == new_ref
        events = job.collect_events()
        assert len(events) == 1
        assert events[0].changes[0].field == "table_ref"

    def test_change_job_config(self):
        """Verify changing job_config registers JobUpdated."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes(job_config={"new_key": True})
        assert job.job_config == {"new_key": True}
        events = job.collect_events()
        assert len(events) == 1
        assert events[0].changes[0].field == "job_config"

    def test_multiple_changes(self):
        """Verify multiple field changes produce one event with multiple FieldChanges."""
        job = _make_job(JobStatus.ACTIVE)
        new_cron = CronExpression(expression="0 3 * * *")
        new_ref = TableReference(catalog="c", table="t")
        job.apply_changes(cron=new_cron, table_ref=new_ref)
        events = job.collect_events()
        assert len(events) == 1
        assert len(events[0].changes) == 2

    def test_no_change_no_event(self):
        """Verify no event is registered when values are unchanged."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes(table_ref=job.table_ref)
        assert job.collect_events() == []

    def test_none_args_ignored(self):
        """Verify None arguments are ignored (no changes applied)."""
        job = _make_job(JobStatus.ACTIVE)
        job.apply_changes()
        assert job.collect_events() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/test_job_transitions.py::TestApplyChanges -v`
Expected: FAIL — `Job` has no `apply_changes` method

- [ ] **Step 3: Add apply_changes() to Job**

Add this method to `B/core/application/domain/model/job/job.py`, after the `trigger()` method. Also add the necessary import for `JobUpdated` and `FieldChange`:

```python
# Add to imports from events
from core.application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from core.application.domain.model.job.field_change import FieldChange

# Add method to Job class:
    def apply_changes(
        self,
        table_ref: TableReference | None = None,
        cron: CronExpression | None = None,
        job_config: dict | None = None,
    ) -> None:
        """Apply configuration changes and register a JobUpdated event if anything changed."""
        changes: list[FieldChange] = []
        if table_ref is not None and table_ref != self.table_ref:
            changes.append(
                FieldChange(field="table_ref", old_value=str(self.table_ref), new_value=str(table_ref))
            )
            self.table_ref = table_ref
        if cron is not None and cron != self.cron:
            changes.append(
                FieldChange(field="cron", old_value=str(self.cron), new_value=str(cron))
            )
            self.cron = cron
        if job_config is not None and job_config != self.job_config:
            changes.append(
                FieldChange(field="job_config", old_value=str(self.job_config), new_value=str(job_config))
            )
            self.job_config = job_config
        if changes:
            self.register_event(JobUpdated(job_id=self.id, changes=tuple(changes)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job/job.py \
        src/table-maintenance/backend/tests/application/domain/model/job/test_job_transitions.py
git commit -m "feat(domain): add Job.apply_changes() with JobUpdated event"
```

---

### Task 7: JobRun.create() Factory Method + Event Registration on Transitions

**Files:**
- Modify: `B/core/application/domain/model/job_run/job_run.py`
- Modify: `T/application/domain/model/job_run/test_job_run.py`
- Modify: `T/application/domain/model/job_run/test_job_run_transitions.py`

- [ ] **Step 1: Write failing tests**

Add to `T/application/domain/model/job_run/test_job_run.py`:

```python
# Add import
from core.application.domain.model.job_run.events import JobRunCreated
from core.application.domain.model.job_run import TriggerType


def test_create_factory_returns_run_with_event():
    """Verify JobRun.create() returns a JobRun and registers a JobRunCreated event."""
    started = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    run = JobRun.create(
        id=JobRunId(value="r1"),
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
        started_at=started,
    )
    assert run.id == JobRunId(value="r1")
    assert run.job_id == JobId(value="j1")
    assert run.status == JobRunStatus.PENDING
    assert run.trigger_type == TriggerType.MANUAL
    assert run.started_at == started
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobRunCreated)
    assert events[0].run_id == JobRunId(value="r1")
    assert events[0].job_id == JobId(value="j1")
    assert events[0].trigger_type == TriggerType.MANUAL
```

Add event assertions to `T/application/domain/model/job_run/test_job_run_transitions.py`:

```python
# Add imports
from core.application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunFailed,
    JobRunStarted,
)

# Add inside TestMarkRunning:
    def test_mark_running_registers_event(self):
        """Verify mark_running registers a JobRunStarted event."""
        run = _make_run(JobRunStatus.PENDING)
        now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
        run.mark_running(now)
        events = run.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobRunStarted)
        assert events[0].started_at == now

# Add inside TestMarkCompleted:
    def test_mark_completed_registers_event(self):
        """Verify mark_completed registers a JobRunCompleted event."""
        run = _make_run(JobRunStatus.RUNNING)
        now = datetime(2026, 4, 25, 13, 0, tzinfo=UTC)
        run.mark_completed(now)
        events = run.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobRunCompleted)
        assert events[0].finished_at == now

# Add inside TestMarkFailed:
    def test_mark_failed_registers_event(self):
        """Verify mark_failed registers a JobRunFailed event."""
        run = _make_run(JobRunStatus.RUNNING)
        now = datetime(2026, 4, 25, 14, 0, tzinfo=UTC)
        run.mark_failed(now)
        events = run.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobRunFailed)
        assert events[0].finished_at == now

# Add inside TestCancel:
    def test_cancel_registers_event(self):
        """Verify cancel registers a JobRunCancelled event."""
        run = _make_run(JobRunStatus.PENDING)
        run.cancel()
        events = run.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], JobRunCancelled)
        assert events[0].run_id == JobRunId(value="run-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_job_run.py::test_create_factory_returns_run_with_event tests/application/domain/model/job_run/test_job_run_transitions.py::TestMarkRunning::test_mark_running_registers_event -v`
Expected: FAIL

- [ ] **Step 3: Update JobRun aggregate**

Replace the full content of `B/core/application/domain/model/job_run/job_run.py`:

```python
"""Define the JobRun aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.aggregate_root import AggregateRoot

from core.application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)
from core.application.domain.model.job_run.exceptions import InvalidStateTransitionError
from core.application.domain.model.job_run.job_run_id import JobRunId
from core.application.domain.model.job_run.job_run_status import JobRunStatus
from core.application.domain.model.job_run.trigger_type import TriggerType

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job.job_id import JobId


@dataclass(eq=False)
class JobRun(AggregateRoot[JobRunId]):
    """A single execution of a Job — the aggregate root for run history."""

    id: JobRunId
    job_id: JobId
    status: JobRunStatus
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @classmethod
    def create(
        cls,
        id: JobRunId,
        job_id: JobId,
        trigger_type: TriggerType,
        started_at: datetime,
    ) -> JobRun:
        """Create a new PENDING JobRun and register a JobRunCreated event."""
        run = cls(
            id=id,
            job_id=job_id,
            status=JobRunStatus.PENDING,
            trigger_type=trigger_type,
            started_at=started_at,
        )
        run.register_event(
            JobRunCreated(run_id=id, job_id=job_id, trigger_type=trigger_type)
        )
        return run

    def _transition_to(self, target: JobRunStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidStateTransitionError(self.status.value, target.value)
        self.status = target

    def mark_running(self, started_at: datetime) -> None:
        """Transition from PENDING to RUNNING."""
        self._transition_to(JobRunStatus.RUNNING)
        self.started_at = started_at
        self.register_event(
            JobRunStarted(run_id=self.id, job_id=self.job_id, started_at=started_at)
        )

    def mark_completed(self, finished_at: datetime) -> None:
        """Transition from RUNNING to COMPLETED."""
        self._transition_to(JobRunStatus.COMPLETED)
        self.finished_at = finished_at
        self.register_event(
            JobRunCompleted(run_id=self.id, job_id=self.job_id, finished_at=finished_at)
        )

    def mark_failed(self, finished_at: datetime) -> None:
        """Transition from PENDING or RUNNING to FAILED."""
        self._transition_to(JobRunStatus.FAILED)
        self.finished_at = finished_at
        self.register_event(
            JobRunFailed(run_id=self.id, job_id=self.job_id, finished_at=finished_at)
        )

    def cancel(self) -> None:
        """Transition from PENDING or RUNNING to CANCELLED."""
        self._transition_to(JobRunStatus.CANCELLED)
        self.register_event(
            JobRunCancelled(run_id=self.id, job_id=self.job_id)
        )
```

- [ ] **Step 4: Run all JobRun model tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/core/application/domain/model/job_run/job_run.py \
        src/table-maintenance/backend/tests/application/domain/model/job_run/test_job_run.py \
        src/table-maintenance/backend/tests/application/domain/model/job_run/test_job_run_transitions.py
git commit -m "feat(domain): add JobRun.create() factory, register events on state transitions"
```

---

### Task 8: JobTriggeredHandler

**Files:**
- Create: `B/core/application/event_handler/job_triggered_handler.py`
- Test: `T/application/event_handler/test_job_triggered_handler.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/event_handler/test_job_triggered_handler.py
"""Tests for JobTriggeredHandler."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from core.application.domain.model.job import JobId
from core.application.domain.model.job.events import JobTriggered
from core.application.domain.model.job_run import JobRunStatus, TriggerType
from core.application.event_handler.job_triggered_handler import JobTriggeredHandler


def test_creates_pending_job_run():
    """Verify handler creates a PENDING JobRun and persists it."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    handler.handle(event)
    repo.create.assert_called_once()
    run = repo.create.call_args[0][0]
    assert run.job_id == JobId(value="j1")
    assert run.status == JobRunStatus.PENDING
    assert run.trigger_type == TriggerType.MANUAL
    assert run.id.value.startswith("j1-")


def test_creates_scheduled_run():
    """Verify handler passes through SCHEDULED trigger type."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.SCHEDULED,
    )
    handler.handle(event)
    run = repo.create.call_args[0][0]
    assert run.trigger_type == TriggerType.SCHEDULED


def test_exposes_last_created_run():
    """Verify handler exposes the created run via last_created_run."""
    repo = MagicMock()
    handler = JobTriggeredHandler(job_runs_repo=repo)
    assert handler.last_created_run is None
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    handler.handle(event)
    assert handler.last_created_run is not None
    assert handler.last_created_run.job_id == JobId(value="j1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_job_triggered_handler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# B/core/application/event_handler/job_triggered_handler.py
"""Define the handler for JobTriggered events."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import JobRun, JobRunId
from core.application.event_handler.event_handler import EventHandler

if TYPE_CHECKING:
    from core.application.domain.model.job.events import JobTriggered
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class JobTriggeredHandler(EventHandler["JobTriggered"]):
    """Handle JobTriggered by creating a new PENDING JobRun.

    After handling, the created run is available via ``last_created_run``.
    This allows synchronous callers (e.g. CreateJobRunService) to
    retrieve the result after dispatching events.
    """

    def __init__(self, job_runs_repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._job_runs_repo = job_runs_repo
        self.last_created_run: JobRun | None = None

    def handle(self, event: JobTriggered) -> None:
        """Create and persist a new JobRun for the triggered job."""
        run = JobRun.create(
            id=JobRunId(value=f"{event.job_id.value}-{secrets.token_hex(3)}"),
            job_id=event.job_id,
            trigger_type=event.trigger_type,
            started_at=datetime.now(UTC),
        )
        self._job_runs_repo.create(run)
        self.last_created_run = run
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_job_triggered_handler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/core/application/event_handler/job_triggered_handler.py \
        src/table-maintenance/backend/tests/application/event_handler/test_job_triggered_handler.py
git commit -m "feat(application): add JobTriggeredHandler for cross-aggregate coordination"
```

---

### Task 9: Update Application Services to Use EventDispatcher

**Files:**
- Modify: `B/core/application/service/job/create_job.py`
- Modify: `B/core/application/service/job/update_job.py`
- Modify: `B/core/application/service/job_run/create_job_run.py`
- Modify: `B/core/application/service/schedule_jobs.py`
- Modify: `B/api/dependencies/use_cases.py`

- [ ] **Step 1: Update CreateJobService**

Replace `B/core/application/service/job/create_job.py`:

```python
"""Define the CreateJobService."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    TableReference,
)
from core.application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)

if TYPE_CHECKING:
    from core.application.event_handler.event_dispatcher import EventDispatcher
    from core.application.port.outbound.job.jobs_repo import JobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Creates a Job definition only. Triggering a run is a separate use case."""

    def __init__(self, repo: JobsRepo, dispatcher: EventDispatcher) -> None:
        """Initialize with the jobs repository and event dispatcher."""
        self._repo = repo
        self._dispatcher = dispatcher

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        """Create a new job from the given input and persist it."""
        job_config = getattr(request, _CONFIG_BY_TYPE[request.job_type], None) or {}
        table = job_config.get("table", "")
        now = datetime.now(UTC)

        job = Job.create(
            id=JobId(value=secrets.token_hex(5)),
            job_type=JobType(request.job_type),
            created_at=now,
            updated_at=now,
            table_ref=TableReference(catalog=request.catalog, table=table),
            job_config=job_config,
            cron=CronExpression(expression=request.cron) if request.cron else None,
            status=JobStatus(request.status),
        )
        job = self._repo.create(job)
        self._dispatcher.dispatch_all(job.collect_events())
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
```

- [ ] **Step 2: Update UpdateJobService**

Replace `B/core/application/service/job/update_job.py`:

```python
"""Define the UpdateJobService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job import (
    CronExpression,
    JobId,
    JobNotFoundError,
    JobStatus,
    TableReference,
)
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    UpdateJobInput,
    UpdateJobOutput,
    UpdateJobUseCase,
)

if TYPE_CHECKING:
    from core.application.event_handler.event_dispatcher import EventDispatcher
    from core.application.port.outbound.job.jobs_repo import JobsRepo

_STATUS_ACTION = {
    JobStatus.ACTIVE: "resume",
    JobStatus.PAUSED: "pause",
    JobStatus.ARCHIVED: "archive",
}


class UpdateJobService(UpdateJobUseCase):
    """Applies a partial update to an existing Job definition."""

    def __init__(self, repo: JobsRepo, dispatcher: EventDispatcher) -> None:
        """Initialize with the jobs repository and event dispatcher."""
        self._repo = repo
        self._dispatcher = dispatcher

    def execute(self, request: UpdateJobInput) -> UpdateJobOutput:
        """Apply partial updates to the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        if request.status is not None:
            target = JobStatus(request.status)
            action = _STATUS_ACTION[target]
            getattr(job, action)()

        job.apply_changes(
            table_ref=TableReference(catalog=request.catalog, table=job.table_ref.table)
            if request.catalog is not None
            else None,
            cron=CronExpression(expression=request.cron)
            if request.cron is not None
            else None,
            job_config=request.job_config,
        )
        job.updated_at = datetime.now(UTC)

        job = self._repo.update(job)
        self._dispatcher.dispatch_all(job.collect_events())

        return UpdateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
```

- [ ] **Step 3: Update CreateJobRunService**

Replace `B/core/application/service/job_run/create_job_run.py`:

```python
"""Define the CreateJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.application.domain.model.job import (
    JobId,
    JobNotActiveError,
    JobNotFoundError,
    MaxActiveRunsExceededError,
)
from core.application.exceptions import JobDisabledError
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    CreateJobRunInput,
    CreateJobRunOutput,
    CreateJobRunUseCase,
)

if TYPE_CHECKING:
    from core.application.event_handler.event_dispatcher import EventDispatcher
    from core.application.event_handler.job_triggered_handler import JobTriggeredHandler
    from core.application.port.outbound.job.jobs_repo import JobsRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CreateJobRunService(CreateJobRunUseCase):
    """Triggers a JobRun via Job.trigger() — only if the Job is active."""

    def __init__(
        self,
        repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        dispatcher: EventDispatcher,
        triggered_handler: JobTriggeredHandler,
    ) -> None:
        """Initialize with repos, event dispatcher, and triggered handler."""
        self._repo = repo
        self._job_runs_repo = job_runs_repo
        self._dispatcher = dispatcher
        self._triggered_handler = triggered_handler

    def execute(self, request: CreateJobRunInput) -> CreateJobRunOutput:
        """Trigger a new execution of the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        active_count = self._job_runs_repo.count_active_for_job(job.id)

        try:
            job.trigger(active_run_count=active_count)
        except JobNotActiveError as e:
            raise JobDisabledError(e.job_id) from e
        except MaxActiveRunsExceededError as e:
            raise JobDisabledError(e.job_id) from e

        self._dispatcher.dispatch_all(job.collect_events())

        run = self._triggered_handler.last_created_run
        if run is None:
            msg = "JobRun was not created by handler"
            raise RuntimeError(msg)
        return CreateJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            trigger_type=run.trigger_type.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
```

- [ ] **Step 4: Update ScheduleJobsService**

Replace `B/core/application/service/schedule_jobs.py`:

```python
"""Define the ScheduleJobsService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import TriggerType
from core.application.service.schedule_jobs_result import ScheduleJobsResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from core.application.event_handler.event_dispatcher import EventDispatcher
    from core.application.port.outbound.job.jobs_repo import JobsRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo

logger = logging.getLogger(__name__)


class ScheduleJobsService:
    """Create JobRuns for jobs whose cron schedule is due."""

    def __init__(
        self,
        jobs_repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        clock: Callable[[], datetime],
        dispatcher: EventDispatcher,
    ) -> None:
        """Initialize with repo dependencies, a clock function, and event dispatcher."""
        self._jobs_repo = jobs_repo
        self._job_runs_repo = job_runs_repo
        self._clock = clock
        self._dispatcher = dispatcher

    def execute(self) -> ScheduleJobsResult:
        """Run one scheduling tick: find due jobs and create pending runs."""
        now = self._clock()
        jobs = self._jobs_repo.list_schedulable(now)
        triggered: list[str] = []

        for job in jobs:
            active = self._job_runs_repo.count_active_for_job(job.id)
            try:
                job.trigger(
                    active_run_count=active,
                    trigger_type=TriggerType.SCHEDULED,
                )
                self._dispatcher.dispatch_all(job.collect_events())
                assert job.cron is not None  # guaranteed by list_schedulable
                next_time = job.cron.next_run_after(now)
                self._jobs_repo.save_next_run_at(job.id, next_time)
                triggered.append(job.id.value)
            except Exception:
                logger.exception("Failed to schedule job %s", job.id.value)

        return ScheduleJobsResult(
            triggered_count=len(triggered),
            job_ids=triggered,
        )
```

- [ ] **Step 5: Update DI layer** (`B/api/dependencies/use_cases.py`)

Add an `EventDispatcher` dependency factory and update all affected use case factories:

```python
# Add these imports at top level:
from core.application.event_handler.event_dispatcher import EventDispatcher
from core.application.event_handler.job_triggered_handler import JobTriggeredHandler
from core.application.domain.model.job.events import JobTriggered

# Add these factory functions:
def get_triggered_handler(
    job_runs_repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> JobTriggeredHandler:
    """Provide the JobTriggeredHandler."""
    return JobTriggeredHandler(job_runs_repo)


def get_event_dispatcher(
    triggered_handler: JobTriggeredHandler = Depends(get_triggered_handler),
) -> EventDispatcher:
    """Provide the EventDispatcher with all registered handlers."""
    dispatcher = EventDispatcher()
    dispatcher.register(JobTriggered, triggered_handler)
    return dispatcher

# Update get_create_job_use_case:
def get_create_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    dispatcher: EventDispatcher = Depends(get_event_dispatcher),
) -> CreateJobUseCase:
    """Provide the CreateJob use case with injected dependencies."""
    return CreateJobService(repo, dispatcher)

# Update get_update_job_use_case:
def get_update_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    dispatcher: EventDispatcher = Depends(get_event_dispatcher),
) -> UpdateJobUseCase:
    """Provide the UpdateJob use case with injected dependencies."""
    return UpdateJobService(repo, dispatcher)

# Update get_create_job_run_use_case:
def get_create_job_run_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    job_runs_repo: JobRunsRepo = Depends(get_job_runs_repo),
    dispatcher: EventDispatcher = Depends(get_event_dispatcher),
    triggered_handler: JobTriggeredHandler = Depends(get_triggered_handler),
) -> CreateJobRunUseCase:
    """Provide the CreateJobRun use case with injected dependencies."""
    return CreateJobRunService(repo, job_runs_repo, dispatcher, triggered_handler)

# Remove get_delete_job_use_case entirely.
# Remove the DeleteJobService import.
# Remove DeleteJobUseCase from TYPE_CHECKING imports.
```

- [ ] **Step 6: Run the full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: Some service-level tests and adapter tests may fail due to changed constructor signatures. Note the failures for the next task.

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/core/application/service/job/create_job.py \
        src/table-maintenance/backend/core/application/service/job/update_job.py \
        src/table-maintenance/backend/core/application/service/job_run/create_job_run.py \
        src/table-maintenance/backend/core/application/service/schedule_jobs.py \
        src/table-maintenance/backend/api/dependencies/use_cases.py
git commit -m "refactor(application): wire EventDispatcher into all application services"
```

---

### Task 10: Remove DeleteJobService and Remap Delete Endpoint to Archive

**Files:**
- Delete: `B/core/application/service/job/delete_job.py`
- Modify: `B/api/adapter/inbound/web/job/delete_job.py`
- Modify: `B/core/application/port/inbound/job/__init__.py`
- Modify: `B/core/application/port/inbound/__init__.py`

- [ ] **Step 1: Remap DELETE endpoint to call archive via UpdateJobService**

Replace `B/api/adapter/inbound/web/job/delete_job.py`:

```python
"""Define the DELETE /jobs/{name} endpoint (archives the job)."""

from __future__ import annotations

from api.dependencies.use_cases import get_update_job_use_case
from fastapi import APIRouter, Depends, HTTPException, Response

from core.application.exceptions import JobNotFoundError
from core.application.port.inbound import UpdateJobInput, UpdateJobUseCase

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(
    name: str,
    use_case: UpdateJobUseCase = Depends(get_update_job_use_case),
):
    """Archive a job by its name (soft delete)."""
    try:
        use_case.execute(UpdateJobInput(job_id=name, status="archived"))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
```

- [ ] **Step 2: Remove DeleteJobService file**

Delete `B/core/application/service/job/delete_job.py`.

- [ ] **Step 3: Clean up port/inbound exports**

Remove `DeleteJobInput`, `DeleteJobOutput`, `DeleteJobUseCase` from:
- `B/core/application/port/inbound/job/__init__.py` — remove the import block and `__all__` entries
- `B/core/application/port/inbound/__init__.py` — remove the imports and `__all__` entries

Do NOT delete the port file `B/core/application/port/inbound/job/delete_job.py` yet — check if any other code references it first. If nothing references it, delete it too.

- [ ] **Step 4: Run the full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: Tests referencing `DeleteJobService` or `DeleteJobUseCase` will fail. Fix those test files by removing or updating them.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(api): remap DELETE endpoint to archive, remove DeleteJobService"
```

---

### Task 11: Fix Remaining Test Failures

**Files:** Various test files that reference old `trigger()` signature, `DeleteJobService`, or old service constructors.

- [ ] **Step 1: Run the full test suite and capture all failures**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v 2>&1 | head -100`

- [ ] **Step 2: Fix each failing test file**

For each failure:
- Tests that call `job.trigger(run_id=..., now=..., active_run_count=...)` → update to `job.trigger(active_run_count=...)` and check events instead of return value
- Tests that construct services without `dispatcher` → add `EventDispatcher()` (no handlers needed for unit tests unless testing dispatch)
- Tests referencing `DeleteJobService` → remove or remap to archive flow

- [ ] **Step 3: Run linter and architecture checks**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

- [ ] **Step 4: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(test): update tests for domain events refactoring"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run complete pre-PR checks**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: All pass.

- [ ] **Step 2: Verify architecture boundaries**

The new `event_handler/` layer sits at `core/application/event_handler/`. Verify that:
- `event_handler/` imports from `domain/model/` and `port/outbound/` (allowed — same layer)
- `domain/model/` does NOT import from `event_handler/` (events are defined in model, handlers in event_handler)
- `adapter/` does NOT import from `event_handler/` directly

- [ ] **Step 3: Commit if any remaining fixes**

```bash
git add -A
git commit -m "chore: final cleanup for domain events implementation"
```
