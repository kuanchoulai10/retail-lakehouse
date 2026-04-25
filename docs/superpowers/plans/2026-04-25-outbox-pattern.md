# Outbox Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace synchronous event dispatch with transactional outbox persistence, and add an independent outbox publisher component that polls and processes events asynchronously.

**Architecture:** Services write domain events to a `domain_event_outbox` SQL table within the same transaction as aggregate changes. A new `ROLE=outbox-publisher` process polls unpublished entries, deserializes them, and dispatches to registered consumers via the existing `EventDispatcher`. The first consumer (`CreateJobRunConsumer`) creates PENDING JobRuns from `JobTriggered` events.

**Tech Stack:** Python dataclasses, SQLAlchemy Core, existing `core.base.EventDispatcher`/`EventHandler`

**Spec:** `docs/superpowers/specs/2026-04-25-outbox-pattern-design.md`

**Shorthand:** `B = src/table-maintenance/backend`, `T = src/table-maintenance/backend/tests`

**Run commands prefix:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend`

---

### Task 1: OutboxEntry Value Object

**Files:**
- Create: `B/core/application/domain/model/outbox_entry.py`
- Test: `T/application/domain/model/test_outbox_entry.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/domain/model/test_outbox_entry.py
"""Tests for OutboxEntry value object."""

from datetime import UTC, datetime

from core.base import ValueObject
from core.application.domain.model.outbox_entry import OutboxEntry


def test_is_value_object():
    """Verify OutboxEntry is a ValueObject subclass."""
    assert issubclass(OutboxEntry, ValueObject)


def test_fields():
    """Verify OutboxEntry stores all fields."""
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    entry = OutboxEntry(
        id="uuid-1",
        aggregate_type="Job",
        aggregate_id="j1",
        event_type="JobTriggered",
        payload='{"job_id": "j1"}',
        occurred_at=ts,
    )
    assert entry.id == "uuid-1"
    assert entry.aggregate_type == "Job"
    assert entry.aggregate_id == "j1"
    assert entry.event_type == "JobTriggered"
    assert entry.payload == '{"job_id": "j1"}'
    assert entry.occurred_at == ts
    assert entry.published_at is None


def test_published_at_can_be_set():
    """Verify published_at can be provided."""
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    entry = OutboxEntry(
        id="uuid-1",
        aggregate_type="Job",
        aggregate_id="j1",
        event_type="JobTriggered",
        payload="{}",
        occurred_at=ts,
        published_at=ts,
    )
    assert entry.published_at == ts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/test_outbox_entry.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# B/core/application/domain/model/outbox_entry.py
"""Define the OutboxEntry value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.value_object import ValueObject

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class OutboxEntry(ValueObject):
    """An immutable record of a domain event pending publication."""

    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: str
    occurred_at: datetime
    published_at: datetime | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/test_outbox_entry.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add B/core/application/domain/model/outbox_entry.py T/application/domain/model/test_outbox_entry.py
git commit -m "feat(domain): add OutboxEntry value object"
```

---

### Task 2: EventOutboxRepo Port

**Files:**
- Create: `B/core/application/port/outbound/event_outbox_repo.py`
- Test: `T/application/port/outbound/test_event_outbox_repo.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/port/outbound/test_event_outbox_repo.py
"""Tests for EventOutboxRepo port interface."""

from abc import ABC

from core.application.port.outbound.event_outbox_repo import EventOutboxRepo


def test_is_abstract():
    """Verify EventOutboxRepo is an ABC."""
    assert issubclass(EventOutboxRepo, ABC)


def test_has_save_method():
    """Verify EventOutboxRepo defines save."""
    assert hasattr(EventOutboxRepo, "save")


def test_has_fetch_unpublished_method():
    """Verify EventOutboxRepo defines fetch_unpublished."""
    assert hasattr(EventOutboxRepo, "fetch_unpublished")


def test_has_mark_published_method():
    """Verify EventOutboxRepo defines mark_published."""
    assert hasattr(EventOutboxRepo, "mark_published")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/test_event_outbox_repo.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# B/core/application/port/outbound/event_outbox_repo.py
"""Define the EventOutboxRepo port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application.domain.model.outbox_entry import OutboxEntry


class EventOutboxRepo(ABC):
    """Port for persisting and retrieving outbox entries."""

    @abstractmethod
    def save(self, entries: list[OutboxEntry]) -> None:
        """Persist outbox entries within the current transaction."""
        ...

    @abstractmethod
    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return up to batch_size unpublished entries ordered by occurred_at."""
        ...

    @abstractmethod
    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at = now for the given entry IDs."""
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/test_event_outbox_repo.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add B/core/application/port/outbound/event_outbox_repo.py T/application/port/outbound/test_event_outbox_repo.py
git commit -m "feat(port): add EventOutboxRepo port interface"
```

---

### Task 3: Outbox SQL Table + SQL Adapter

**Files:**
- Create: `B/core/adapter/outbound/sql/outbox_table.py`
- Create: `B/core/adapter/outbound/sql/event_outbox_sql_repo.py`
- Test: `T/adapter/outbound/sql/test_event_outbox_sql_repo.py`

- [ ] **Step 1: Write the failing test**

```python
# T/adapter/outbound/sql/test_event_outbox_sql_repo.py
"""Tests for EventOutboxSqlRepo."""

from datetime import UTC, datetime

from sqlalchemy import create_engine

from core.adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from core.adapter.outbound.sql.metadata import metadata
from core.application.domain.model.outbox_entry import OutboxEntry
from core.application.port.outbound.event_outbox_repo import EventOutboxRepo


def _make_repo():
    """Create an in-memory SQLite repo for testing."""
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return EventOutboxSqlRepo(engine)


def _make_entry(entry_id: str = "e1", event_type: str = "JobTriggered") -> OutboxEntry:
    return OutboxEntry(
        id=entry_id,
        aggregate_type="Job",
        aggregate_id="j1",
        event_type=event_type,
        payload='{"job_id": "j1"}',
        occurred_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )


def test_implements_port():
    """Verify EventOutboxSqlRepo implements EventOutboxRepo."""
    assert issubclass(EventOutboxSqlRepo, EventOutboxRepo)


def test_save_and_fetch_unpublished():
    """Verify saved entries are returned by fetch_unpublished."""
    repo = _make_repo()
    entry = _make_entry()
    repo.save([entry])
    result = repo.fetch_unpublished()
    assert len(result) == 1
    assert result[0].id == "e1"
    assert result[0].published_at is None


def test_fetch_unpublished_ignores_published():
    """Verify published entries are not returned."""
    repo = _make_repo()
    repo.save([_make_entry("e1"), _make_entry("e2")])
    repo.mark_published(["e1"])
    result = repo.fetch_unpublished()
    assert len(result) == 1
    assert result[0].id == "e2"


def test_mark_published_sets_timestamp():
    """Verify mark_published sets published_at."""
    repo = _make_repo()
    repo.save([_make_entry()])
    repo.mark_published(["e1"])
    result = repo.fetch_unpublished()
    assert result == []


def test_fetch_unpublished_respects_batch_size():
    """Verify batch_size limits results."""
    repo = _make_repo()
    repo.save([_make_entry("e1"), _make_entry("e2"), _make_entry("e3")])
    result = repo.fetch_unpublished(batch_size=2)
    assert len(result) == 2


def test_fetch_unpublished_ordered_by_occurred_at():
    """Verify results are ordered by occurred_at ascending."""
    repo = _make_repo()
    early = OutboxEntry(
        id="e1", aggregate_type="Job", aggregate_id="j1",
        event_type="JobCreated", payload="{}",
        occurred_at=datetime(2026, 4, 25, 10, 0, tzinfo=UTC),
    )
    late = OutboxEntry(
        id="e2", aggregate_type="Job", aggregate_id="j1",
        event_type="JobTriggered", payload="{}",
        occurred_at=datetime(2026, 4, 25, 14, 0, tzinfo=UTC),
    )
    repo.save([late, early])
    result = repo.fetch_unpublished()
    assert result[0].id == "e1"
    assert result[1].id == "e2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/sql/test_event_outbox_sql_repo.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create outbox table definition**

```python
# B/core/adapter/outbound/sql/outbox_table.py
"""Define the domain_event_outbox SQLAlchemy table schema."""

from sqlalchemy import Column, DateTime, String, Table

from core.adapter.outbound.sql.metadata import metadata

outbox_table = Table(
    "domain_event_outbox",
    metadata,
    Column("id", String, primary_key=True),
    Column("aggregate_type", String, nullable=False),
    Column("aggregate_id", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("payload", String, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
)
```

- [ ] **Step 4: Create SQL repo implementation**

```python
# B/core/adapter/outbound/sql/event_outbox_sql_repo.py
"""Define the EventOutboxSqlRepo adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update

from core.adapter.outbound.sql.outbox_table import outbox_table
from core.application.domain.model.outbox_entry import OutboxEntry
from core.application.port.outbound.event_outbox_repo import EventOutboxRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine


class EventOutboxSqlRepo(EventOutboxRepo):
    """EventOutboxRepo backed by a SQLAlchemy Engine."""

    def __init__(self, engine: Engine) -> None:
        """Initialize with a SQLAlchemy engine."""
        self._engine = engine

    def save(self, entries: list[OutboxEntry]) -> None:
        """Insert outbox entries."""
        if not entries:
            return
        with self._engine.begin() as conn:
            for entry in entries:
                conn.execute(
                    insert(outbox_table).values(
                        id=entry.id,
                        aggregate_type=entry.aggregate_type,
                        aggregate_id=entry.aggregate_id,
                        event_type=entry.event_type,
                        payload=entry.payload,
                        occurred_at=entry.occurred_at,
                        published_at=entry.published_at,
                    )
                )

    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return unpublished entries ordered by occurred_at."""
        stmt = (
            select(outbox_table)
            .where(outbox_table.c.published_at.is_(None))
            .order_by(outbox_table.c.occurred_at)
            .limit(batch_size)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            OutboxEntry(
                id=row["id"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                payload=row["payload"],
                occurred_at=row["occurred_at"],
                published_at=row["published_at"],
            )
            for row in rows
        ]

    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at for the given IDs."""
        if not entry_ids:
            return
        stmt = (
            update(outbox_table)
            .where(outbox_table.c.id.in_(entry_ids))
            .values(published_at=datetime.now(UTC))
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/sql/test_event_outbox_sql_repo.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add B/core/adapter/outbound/sql/outbox_table.py B/core/adapter/outbound/sql/event_outbox_sql_repo.py T/adapter/outbound/sql/test_event_outbox_sql_repo.py
git commit -m "feat(adapter): add outbox SQL table and EventOutboxSqlRepo"
```

---

### Task 4: EventSerializer

**Files:**
- Create: `B/core/application/event_handler/event_serializer.py`
- Test: `T/application/event_handler/test_event_serializer.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/event_handler/test_event_serializer.py
"""Tests for EventSerializer."""

import json
from datetime import UTC, datetime

from core.application.domain.model.job import JobId, TableReference, JobType, CronExpression
from core.application.domain.model.job.events import JobCreated, JobTriggered, JobPaused
from core.application.domain.model.job_run import TriggerType
from core.application.domain.model.outbox_entry import OutboxEntry
from core.application.event_handler.event_serializer import EventSerializer


def _make_serializer() -> EventSerializer:
    return EventSerializer()


class TestSerialize:
    """Tests for EventSerializer.serialize()."""

    def test_serialize_job_triggered(self):
        """Verify JobTriggered serializes to JSON string."""
        s = _make_serializer()
        event = JobTriggered(
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.MANUAL,
        )
        result = s.serialize(event)
        data = json.loads(result)
        assert data["job_id"] == "j1"
        assert data["trigger_type"] == "manual"

    def test_serialize_job_paused(self):
        """Verify JobPaused serializes to JSON string."""
        s = _make_serializer()
        event = JobPaused(job_id=JobId(value="j1"))
        result = s.serialize(event)
        data = json.loads(result)
        assert data["job_id"] == "j1"

    def test_serialize_job_created_with_cron_none(self):
        """Verify JobCreated with cron=None serializes correctly."""
        s = _make_serializer()
        event = JobCreated(
            job_id=JobId(value="j1"),
            job_type=JobType.EXPIRE_SNAPSHOTS,
            table_ref=TableReference(catalog="cat", table="tbl"),
            cron=None,
        )
        result = s.serialize(event)
        data = json.loads(result)
        assert data["cron"] is None


class TestDeserialize:
    """Tests for EventSerializer.deserialize()."""

    def test_roundtrip_job_triggered(self):
        """Verify serialize then deserialize produces equivalent event."""
        s = _make_serializer()
        original = JobTriggered(
            job_id=JobId(value="j1"),
            trigger_type=TriggerType.SCHEDULED,
        )
        payload = s.serialize(original)
        restored = s.deserialize("JobTriggered", payload)
        assert isinstance(restored, JobTriggered)
        assert restored.job_id == JobId(value="j1")
        assert restored.trigger_type == TriggerType.SCHEDULED

    def test_roundtrip_job_paused(self):
        """Verify serialize then deserialize produces equivalent event."""
        s = _make_serializer()
        original = JobPaused(job_id=JobId(value="j1"))
        payload = s.serialize(original)
        restored = s.deserialize("JobPaused", payload)
        assert isinstance(restored, JobPaused)
        assert restored.job_id == JobId(value="j1")


class TestToOutboxEntries:
    """Tests for EventSerializer.to_outbox_entries()."""

    def test_converts_events_to_entries(self):
        """Verify events are converted to OutboxEntry list."""
        s = _make_serializer()
        events = [
            JobTriggered(
                job_id=JobId(value="j1"),
                trigger_type=TriggerType.MANUAL,
            ),
        ]
        entries = s.to_outbox_entries(events, aggregate_type="Job", aggregate_id="j1")
        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, OutboxEntry)
        assert entry.aggregate_type == "Job"
        assert entry.aggregate_id == "j1"
        assert entry.event_type == "JobTriggered"
        assert entry.published_at is None
        assert entry.id  # UUID should be generated

    def test_multiple_events(self):
        """Verify multiple events produce multiple entries."""
        s = _make_serializer()
        events = [
            JobPaused(job_id=JobId(value="j1")),
            JobTriggered(job_id=JobId(value="j1"), trigger_type=TriggerType.MANUAL),
        ]
        entries = s.to_outbox_entries(events, aggregate_type="Job", aggregate_id="j1")
        assert len(entries) == 2
        assert entries[0].event_type == "JobPaused"
        assert entries[1].event_type == "JobTriggered"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_event_serializer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# B/core/application/event_handler/event_serializer.py
"""Define the EventSerializer for outbox persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, fields
from datetime import datetime
from typing import ClassVar

from core.base.domain_event import DomainEvent

from core.application.domain.model.job.cron_expression import CronExpression
from core.application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from core.application.domain.model.job.field_change import FieldChange
from core.application.domain.model.job.job_id import JobId
from core.application.domain.model.job.job_type import JobType
from core.application.domain.model.job.table_reference import TableReference
from core.application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)
from core.application.domain.model.job_run.job_run_id import JobRunId
from core.application.domain.model.job_run.trigger_type import TriggerType
from core.application.domain.model.outbox_entry import OutboxEntry


class EventSerializer:
    """Serialize and deserialize domain events to/from JSON for outbox storage."""

    _REGISTRY: ClassVar[dict[str, type[DomainEvent]]] = {
        "JobCreated": JobCreated,
        "JobUpdated": JobUpdated,
        "JobPaused": JobPaused,
        "JobResumed": JobResumed,
        "JobArchived": JobArchived,
        "JobTriggered": JobTriggered,
        "JobRunCreated": JobRunCreated,
        "JobRunStarted": JobRunStarted,
        "JobRunCompleted": JobRunCompleted,
        "JobRunFailed": JobRunFailed,
        "JobRunCancelled": JobRunCancelled,
    }

    def serialize(self, event: DomainEvent) -> str:
        """Convert a domain event to a JSON string."""
        raw = asdict(event)
        raw.pop("occurred_at", None)
        return json.dumps(raw, default=self._json_default)

    def deserialize(self, event_type: str, payload: str) -> DomainEvent:
        """Reconstruct a domain event from its type name and JSON payload."""
        cls = self._REGISTRY[event_type]
        data = json.loads(payload)
        return self._reconstruct(cls, data)

    def to_outbox_entries(
        self,
        events: list[DomainEvent],
        aggregate_type: str,
        aggregate_id: str,
    ) -> list[OutboxEntry]:
        """Convert domain events to outbox entries ready for persistence."""
        return [
            OutboxEntry(
                id=str(uuid.uuid4()),
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=type(event).__name__,
                payload=self.serialize(event),
                occurred_at=event.occurred_at,
            )
            for event in events
        ]

    @staticmethod
    def _json_default(obj: object) -> object:
        """Handle domain types during JSON serialization."""
        if hasattr(obj, "value"):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, tuple):
            return [
                {"field": fc.field, "old_value": fc.old_value, "new_value": fc.new_value}
                if hasattr(fc, "field")
                else fc
                for fc in obj
            ]
        raise TypeError(f"Cannot serialize {type(obj)}")

    def _reconstruct(self, cls: type[DomainEvent], data: dict) -> DomainEvent:
        """Reconstruct a domain event from raw dict, rebuilding domain types."""
        field_types = {f.name: f.type for f in fields(cls) if f.name != "occurred_at"}
        kwargs = {}
        for name, value in data.items():
            if name == "occurred_at":
                continue
            kwargs[name] = self._rebuild_field(name, value, field_types.get(name))
        return cls(**kwargs)

    def _rebuild_field(self, name: str, value: object, type_hint: object) -> object:
        """Rebuild a single field value to its domain type."""
        if value is None:
            return None
        if name == "job_id":
            return JobId(value=value)
        if name == "run_id":
            return JobRunId(value=value)
        if name == "job_type":
            return JobType(value)
        if name == "trigger_type":
            return TriggerType(value)
        if name == "table_ref":
            return TableReference(catalog=value["catalog"], table=value["table"])
        if name == "cron":
            return CronExpression(expression=value) if value else None
        if name == "changes":
            return tuple(
                FieldChange(field=c["field"], old_value=c["old_value"], new_value=c["new_value"])
                for c in value
            )
        if name in ("started_at", "finished_at"):
            return datetime.fromisoformat(value) if isinstance(value, str) else value
        return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_event_serializer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add B/core/application/event_handler/event_serializer.py T/application/event_handler/test_event_serializer.py
git commit -m "feat(application): add EventSerializer for outbox persistence"
```

---

### Task 5: Update Services to Write to Outbox

**Files:**
- Modify: `B/core/application/service/job/create_job.py`
- Modify: `B/core/application/service/job/update_job.py`
- Modify: `B/core/application/service/job_run/create_job_run.py`
- Modify: `B/core/application/service/schedule_jobs.py`
- Create: `B/core/application/port/inbound/job_run/trigger_job/__init__.py`
- Modify: `B/core/application/port/inbound/job_run/__init__.py`
- Test: existing service tests will be updated

- [ ] **Step 1: Create TriggerJobOutput**

Create the new inbound port for the trigger use case output:

```python
# B/core/application/port/inbound/job_run/trigger_job/__init__.py
"""TriggerJob use case definition."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerJobOutput:
    """Output of the trigger-job use case (async — no run_id yet)."""

    job_id: str
    accepted: bool = True
```

- [ ] **Step 2: Update CreateJobService**

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
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.application.port.outbound.job.jobs_repo import JobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Creates a Job definition only. Triggering a run is a separate use case."""

    def __init__(
        self, repo: JobsRepo, outbox_repo: EventOutboxRepo, serializer: EventSerializer
    ) -> None:
        """Initialize with the jobs repository, outbox repo, and serializer."""
        self._repo = repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

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
        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
```

- [ ] **Step 3: Update UpdateJobService**

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
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.application.port.outbound.job.jobs_repo import JobsRepo

_STATUS_ACTION = {
    JobStatus.ACTIVE: "resume",
    JobStatus.PAUSED: "pause",
    JobStatus.ARCHIVED: "archive",
}


class UpdateJobService(UpdateJobUseCase):
    """Applies a partial update to an existing Job definition."""

    def __init__(
        self, repo: JobsRepo, outbox_repo: EventOutboxRepo, serializer: EventSerializer
    ) -> None:
        """Initialize with the jobs repository, outbox repo, and serializer."""
        self._repo = repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

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
        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)

        return UpdateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
```

- [ ] **Step 4: Update CreateJobRunService**

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
    CreateJobRunUseCase,
)
from core.application.port.inbound.job_run.trigger_job import TriggerJobOutput

if TYPE_CHECKING:
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.application.port.outbound.job.jobs_repo import JobsRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CreateJobRunService(CreateJobRunUseCase):
    """Triggers a JobRun via Job.trigger() — writes event to outbox for async processing."""

    def __init__(
        self,
        repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with repos, outbox repo, and serializer."""
        self._repo = repo
        self._job_runs_repo = job_runs_repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self, request: CreateJobRunInput) -> TriggerJobOutput:
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

        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)

        return TriggerJobOutput(job_id=job.id.value)
```

- [ ] **Step 5: Update ScheduleJobsService**

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

    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
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
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with repo dependencies, clock, outbox repo, and serializer."""
        self._jobs_repo = jobs_repo
        self._job_runs_repo = job_runs_repo
        self._clock = clock
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self) -> ScheduleJobsResult:
        """Run one scheduling tick: find due jobs and write trigger events to outbox."""
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
                entries = self._serializer.to_outbox_entries(
                    events=job.collect_events(),
                    aggregate_type="Job",
                    aggregate_id=job.id.value,
                )
                self._outbox_repo.save(entries)
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

- [ ] **Step 6: Update API endpoint for 202**

Replace `B/api/adapter/inbound/web/job_run/create_job_run.py`:

```python
"""Define the POST /jobs/{name}/runs endpoint."""

from __future__ import annotations

from api.dependencies.use_cases import get_create_job_run_use_case
from fastapi import APIRouter, Depends, HTTPException

from core.application.exceptions import JobDisabledError, JobNotFoundError
from core.application.port.inbound import CreateJobRunInput, CreateJobRunUseCase

router = APIRouter()


@router.post(
    "/jobs/{name}/runs",
    status_code=202,
)
def create_job_run(
    name: str,
    use_case: CreateJobRunUseCase = Depends(get_create_job_run_use_case),
):
    """Trigger a new run for the specified job (async — run created by outbox consumer)."""
    try:
        result = use_case.execute(CreateJobRunInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except JobDisabledError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {"job_id": result.job_id, "accepted": result.accepted}
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(application): services write events to outbox instead of sync dispatch"
```

---

### Task 6: CreateJobRunConsumer (rename from JobTriggeredHandler)

**Files:**
- Create: `B/core/application/event_handler/create_job_run_consumer.py`
- Delete: `B/core/application/event_handler/job_triggered_handler.py`
- Test: `T/application/event_handler/test_create_job_run_consumer.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/event_handler/test_create_job_run_consumer.py
"""Tests for CreateJobRunConsumer."""

from unittest.mock import MagicMock

from core.application.domain.model.job import JobId
from core.application.domain.model.job.events import JobTriggered
from core.application.domain.model.job_run import JobRunStatus, TriggerType
from core.application.event_handler.create_job_run_consumer import CreateJobRunConsumer


def test_creates_pending_job_run():
    """Verify consumer creates a PENDING JobRun and persists it."""
    job_runs_repo = MagicMock()
    job_runs_repo.create.side_effect = lambda run: run
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = []
    consumer = CreateJobRunConsumer(
        job_runs_repo=job_runs_repo,
        outbox_repo=outbox_repo,
        serializer=serializer,
    )
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    consumer.handle(event)
    job_runs_repo.create.assert_called_once()
    run = job_runs_repo.create.call_args[0][0]
    assert run.job_id == JobId(value="j1")
    assert run.status == JobRunStatus.PENDING
    assert run.trigger_type == TriggerType.MANUAL
    assert run.id.value.startswith("j1-")


def test_writes_job_run_events_to_outbox():
    """Verify consumer writes JobRunCreated event to outbox."""
    job_runs_repo = MagicMock()
    job_runs_repo.create.side_effect = lambda run: run
    outbox_repo = MagicMock()
    serializer = MagicMock()
    serializer.to_outbox_entries.return_value = [MagicMock()]
    consumer = CreateJobRunConsumer(
        job_runs_repo=job_runs_repo,
        outbox_repo=outbox_repo,
        serializer=serializer,
    )
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
    )
    consumer.handle(event)
    serializer.to_outbox_entries.assert_called_once()
    outbox_repo.save.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_create_job_run_consumer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# B/core/application/event_handler/create_job_run_consumer.py
"""Define the consumer for JobTriggered events."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import JobRun, JobRunId
from core.base.event_handler import EventHandler

if TYPE_CHECKING:
    from core.application.domain.model.job.events import JobTriggered
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CreateJobRunConsumer(EventHandler["JobTriggered"]):
    """Handle JobTriggered by creating a new PENDING JobRun.

    Writes the JobRun's own events (JobRunCreated) to the outbox
    for downstream consumers.
    """

    def __init__(
        self,
        job_runs_repo: JobRunsRepo,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with job runs repo, outbox repo, and serializer."""
        self._job_runs_repo = job_runs_repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def handle(self, event: JobTriggered) -> None:
        """Create and persist a new JobRun, write its events to outbox."""
        run = JobRun.create(
            id=JobRunId(value=f"{event.job_id.value}-{secrets.token_hex(3)}"),
            job_id=event.job_id,
            trigger_type=event.trigger_type,
            started_at=datetime.now(UTC),
        )
        self._job_runs_repo.create(run)
        entries = self._serializer.to_outbox_entries(
            events=run.collect_events(),
            aggregate_type="JobRun",
            aggregate_id=run.id.value,
        )
        self._outbox_repo.save(entries)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/event_handler/test_create_job_run_consumer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Delete old handler and its test**

Delete `B/core/application/event_handler/job_triggered_handler.py` and `T/application/event_handler/test_job_triggered_handler.py`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(application): rename JobTriggeredHandler to CreateJobRunConsumer with outbox writes"
```

---

### Task 7: OutboxPublisherService

**Files:**
- Create: `B/core/application/service/outbox_publisher.py`
- Create: `B/core/application/service/outbox_publish_result.py`
- Test: `T/application/service/test_outbox_publisher.py`

- [ ] **Step 1: Write the failing test**

```python
# T/application/service/test_outbox_publisher.py
"""Tests for OutboxPublisherService."""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import MagicMock

from core.base import DomainEvent
from core.base.event_dispatcher import EventDispatcher
from core.base.event_handler import EventHandler
from core.application.domain.model.outbox_entry import OutboxEntry
from core.application.service.outbox_publisher import OutboxPublisherService


@dataclass(frozen=True)
class _StubEvent(DomainEvent):
    value: str


class _RecordingHandler(EventHandler[_StubEvent]):
    def __init__(self) -> None:
        self.events: list[_StubEvent] = []

    def handle(self, event: _StubEvent) -> None:
        self.events.append(event)


def _make_entry(entry_id: str = "e1", event_type: str = "JobTriggered") -> OutboxEntry:
    return OutboxEntry(
        id=entry_id,
        aggregate_type="Job",
        aggregate_id="j1",
        event_type=event_type,
        payload='{"job_id": "j1", "trigger_type": "manual"}',
        occurred_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )


def test_publishes_unpublished_entries():
    """Verify service fetches, dispatches, and marks entries as published."""
    outbox_repo = MagicMock()
    outbox_repo.fetch_unpublished.return_value = [_make_entry()]
    serializer = MagicMock()
    stub_event = _StubEvent(value="test")
    serializer.deserialize.return_value = stub_event
    dispatcher = EventDispatcher()
    handler = _RecordingHandler()
    dispatcher.register(_StubEvent, handler)

    service = OutboxPublisherService(outbox_repo, serializer, dispatcher)
    result = service.execute()

    assert result.published_count == 1
    outbox_repo.mark_published.assert_called_once_with(["e1"])
    serializer.deserialize.assert_called_once_with("JobTriggered", '{"job_id": "j1", "trigger_type": "manual"}')


def test_no_entries_returns_zero():
    """Verify service returns zero when no unpublished entries."""
    outbox_repo = MagicMock()
    outbox_repo.fetch_unpublished.return_value = []
    serializer = MagicMock()
    dispatcher = EventDispatcher()

    service = OutboxPublisherService(outbox_repo, serializer, dispatcher)
    result = service.execute()

    assert result.published_count == 0
    outbox_repo.mark_published.assert_not_called()


def test_handles_multiple_entries():
    """Verify service processes all entries in batch."""
    outbox_repo = MagicMock()
    outbox_repo.fetch_unpublished.return_value = [_make_entry("e1"), _make_entry("e2")]
    serializer = MagicMock()
    serializer.deserialize.return_value = _StubEvent(value="x")
    dispatcher = EventDispatcher()

    service = OutboxPublisherService(outbox_repo, serializer, dispatcher)
    result = service.execute()

    assert result.published_count == 2
    outbox_repo.mark_published.assert_called_once_with(["e1", "e2"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/test_outbox_publisher.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create OutboxPublishResult**

```python
# B/core/application/service/outbox_publish_result.py
"""Define the OutboxPublishResult."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutboxPublishResult:
    """Result of one outbox publishing tick."""

    published_count: int
```

- [ ] **Step 4: Create OutboxPublisherService**

```python
# B/core/application/service/outbox_publisher.py
"""Define the OutboxPublisherService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.application.service.outbox_publish_result import OutboxPublishResult

if TYPE_CHECKING:
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.base.event_dispatcher import EventDispatcher


class OutboxPublisherService:
    """Fetch unpublished outbox entries, dispatch events, mark as published."""

    def __init__(
        self,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
        dispatcher: EventDispatcher,
    ) -> None:
        """Initialize with outbox repo, serializer, and event dispatcher."""
        self._outbox_repo = outbox_repo
        self._serializer = serializer
        self._dispatcher = dispatcher

    def execute(self) -> OutboxPublishResult:
        """One tick: fetch unpublished → deserialize → dispatch → mark published."""
        entries = self._outbox_repo.fetch_unpublished(batch_size=100)
        if not entries:
            return OutboxPublishResult(published_count=0)

        for entry in entries:
            event = self._serializer.deserialize(entry.event_type, entry.payload)
            self._dispatcher.dispatch(event)

        self._outbox_repo.mark_published([e.id for e in entries])
        return OutboxPublishResult(published_count=len(entries))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/test_outbox_publisher.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add B/core/application/service/outbox_publisher.py B/core/application/service/outbox_publish_result.py T/application/service/test_outbox_publisher.py
git commit -m "feat(application): add OutboxPublisherService"
```

---

### Task 8: Outbox Publisher Entry Point

**Files:**
- Create: `B/outbox_publisher/__init__.py`
- Create: `B/outbox_publisher/publisher_loop.py`
- Create: `B/outbox_publisher/main.py`
- Modify: `B/entrypoint.py`
- Test: `T/outbox_publisher/__init__.py`
- Test: `T/outbox_publisher/test_publisher_loop.py`

- [ ] **Step 1: Write the failing test for PublisherLoop**

```python
# T/outbox_publisher/__init__.py
```

```python
# T/outbox_publisher/test_publisher_loop.py
"""Tests for PublisherLoop."""

from unittest.mock import MagicMock

from core.application.service.outbox_publish_result import OutboxPublishResult
from outbox_publisher.publisher_loop import PublisherLoop


def test_tick_calls_service_execute():
    """Verify tick calls the publisher service."""
    service = MagicMock()
    service.execute.return_value = OutboxPublishResult(published_count=3)
    loop = PublisherLoop(service, interval_seconds=5)
    loop.tick()
    service.execute.assert_called_once()


def test_tick_does_not_raise_on_service_exception():
    """Verify tick logs and swallows exceptions."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("boom")
    loop = PublisherLoop(service, interval_seconds=5)
    loop.tick()  # should not raise


def test_loop_stops_on_shutdown_event():
    """Verify start returns after stop is called."""
    service = MagicMock()
    service.execute.return_value = OutboxPublishResult(published_count=0)
    loop = PublisherLoop(service, interval_seconds=60)
    loop.stop()
    loop.start()  # should return immediately
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/outbox_publisher/test_publisher_loop.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create PublisherLoop**

```python
# B/outbox_publisher/__init__.py
```

```python
# B/outbox_publisher/publisher_loop.py
"""Define the outbox publisher polling loop."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application.service.outbox_publisher import OutboxPublisherService

logger = logging.getLogger(__name__)


class PublisherLoop:
    """Poll the outbox table and dispatch events on a fixed interval."""

    def __init__(
        self, service: OutboxPublisherService, interval_seconds: int = 5
    ) -> None:
        """Initialize with a publisher service and polling interval."""
        self._service = service
        self._interval = interval_seconds
        self._stop = threading.Event()

    def tick(self) -> None:
        """Run one publishing iteration."""
        try:
            result = self._service.execute()
            if result.published_count > 0:
                logger.info(
                    "Outbox tick: published %d event(s)", result.published_count
                )
        except Exception:
            logger.exception("Outbox tick failed")

    def start(self) -> None:
        """Start the polling loop until stop() is called."""
        logger.info("Outbox publisher started (interval=%ds)", self._interval)
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self._interval)
        logger.info("Outbox publisher stopped")

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._stop.set()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/outbox_publisher/test_publisher_loop.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Create outbox_publisher/main.py**

```python
# B/outbox_publisher/main.py
"""Outbox publisher entry point — polls outbox table and dispatches events."""

from __future__ import annotations

import logging
import os
import signal
from datetime import UTC, datetime

from core.adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from core.adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from core.adapter.outbound.sql.metadata import metadata
from core.application.domain.model.job.events import JobTriggered
from core.application.event_handler.create_job_run_consumer import CreateJobRunConsumer
from core.application.event_handler.event_serializer import EventSerializer
from core.application.service.outbox_publisher import OutboxPublisherService
from core.base.event_dispatcher import EventDispatcher
from outbox_publisher.publisher_loop import PublisherLoop
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_publisher() -> PublisherLoop:
    """Wire up the outbox publisher with SQL repos and return the loop."""
    database_url = os.environ.get(
        "OUTBOX_DATABASE_URL",
        "sqlite:///scheduler.db",
    )
    interval = int(os.environ.get("OUTBOX_INTERVAL_SECONDS", "5"))

    engine = create_engine(database_url)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        CreateJobRunConsumer(job_runs_repo, outbox_repo, serializer),
    )

    service = OutboxPublisherService(outbox_repo, serializer, dispatcher)
    return PublisherLoop(service, interval_seconds=interval)


def main() -> None:
    """Start the outbox publisher."""
    publisher = build_publisher()
    signal.signal(signal.SIGTERM, lambda *_: publisher.stop())
    signal.signal(signal.SIGINT, lambda *_: publisher.stop())
    logger.info("Starting outbox publisher")
    publisher.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Update entrypoint.py**

Replace `B/entrypoint.py`:

```python
"""Entry point: selects api, scheduler, or outbox-publisher role via ROLE env var."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Dispatch to api, scheduler, or outbox-publisher based on ROLE env var."""
    role = os.environ.get("ROLE", "api")

    if role == "api":
        import uvicorn

        uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
    elif role == "scheduler":
        from scheduler.main import main as scheduler_main

        scheduler_main()
    elif role == "outbox-publisher":
        from outbox_publisher.main import main as publisher_main

        publisher_main()
    else:
        print(
            f"Unknown ROLE: {role!r}. Use 'api', 'scheduler', or 'outbox-publisher'.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Commit**

```bash
git add B/outbox_publisher/ B/entrypoint.py T/outbox_publisher/
git commit -m "feat(outbox-publisher): add outbox publisher entry point and polling loop"
```

---

### Task 9: Update DI Layer + Scheduler + Import Linter

**Files:**
- Delete: `B/api/dependencies/event_dispatcher.py`
- Modify: `B/api/dependencies/use_cases.py`
- Modify: `B/scheduler/main.py`
- Modify: `B/.importlinter`

- [ ] **Step 1: Create outbox DI module**

```python
# B/api/dependencies/outbox.py
"""Provide outbox dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from core.adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from core.application.event_handler.event_serializer import EventSerializer

from api.dependencies.repos import get_engine

if TYPE_CHECKING:
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo


def get_event_serializer() -> EventSerializer:
    """Provide the EventSerializer."""
    return EventSerializer()


def get_outbox_repo(
    engine=Depends(get_engine),
) -> EventOutboxRepo:
    """Provide the EventOutboxRepo."""
    return EventOutboxSqlRepo(engine)
```

Note: `get_engine` may need to be added to `api/dependencies/repos.py` if it doesn't exist. Check the existing code and adapt.

- [ ] **Step 2: Update use_cases.py**

Remove all `EventDispatcher` and `JobTriggeredHandler` references. Replace with `EventOutboxRepo` + `EventSerializer`.

Key changes:
- Remove imports of `EventDispatcher`, `JobTriggeredHandler`, `get_event_dispatcher`, `get_triggered_handler`
- Add imports of `get_outbox_repo`, `get_event_serializer`
- Update `get_create_job_use_case`, `get_update_job_use_case`, `get_create_job_run_use_case` to use outbox deps

- [ ] **Step 3: Delete event_dispatcher.py DI module**

Delete `B/api/dependencies/event_dispatcher.py`.

- [ ] **Step 4: Update scheduler/main.py**

Replace to use outbox instead of EventDispatcher:

```python
"""Scheduler entry point — polls DB and writes trigger events to outbox."""

from __future__ import annotations

import logging
import os
import signal
from datetime import UTC, datetime

from core.adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from core.adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from core.adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from core.adapter.outbound.sql.metadata import metadata
from core.application.event_handler.event_serializer import EventSerializer
from core.application.service.schedule_jobs import ScheduleJobsService
from scheduler.scheduler_loop import SchedulerLoop
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_scheduler() -> SchedulerLoop:
    """Wire up the scheduler with SQL repos and return the loop."""
    database_url = os.environ.get(
        "SCHEDULER_DATABASE_URL",
        "sqlite:///scheduler.db",
    )
    interval = int(os.environ.get("SCHEDULER_INTERVAL_SECONDS", "30"))

    engine = create_engine(database_url)
    metadata.create_all(engine)

    jobs_repo = JobsSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    outbox_repo = EventOutboxSqlRepo(engine)
    serializer = EventSerializer()

    service = ScheduleJobsService(
        jobs_repo,
        job_runs_repo,
        clock=lambda: datetime.now(UTC),
        outbox_repo=outbox_repo,
        serializer=serializer,
    )
    return SchedulerLoop(service, interval_seconds=interval)


def main() -> None:
    """Start the scheduler."""
    scheduler = build_scheduler()
    signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
    signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
    logger.info("Starting table-maintenance scheduler")
    scheduler.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Update .importlinter**

Add `outbox_publisher` to root_packages and add isolation rules:

```ini
[importlinter]
root_packages =
    core
    api
    scheduler
    outbox_publisher
```

Add contracts:
```ini
[importlinter:contract:outbox-publisher-no-api]
name = Outbox publisher does not depend on API
type = forbidden
source_modules =
    outbox_publisher
forbidden_modules =
    api
    fastapi

[importlinter:contract:outbox-publisher-no-scheduler]
name = Outbox publisher does not depend on scheduler
type = forbidden
source_modules =
    outbox_publisher
forbidden_modules =
    scheduler

[importlinter:contract:api-no-outbox-publisher]
name = API does not depend on outbox publisher
type = forbidden
source_modules =
    api
forbidden_modules =
    outbox_publisher

[importlinter:contract:scheduler-no-outbox-publisher]
name = Scheduler does not depend on outbox publisher
type = forbidden
source_modules =
    scheduler
forbidden_modules =
    outbox_publisher
```

Update existing ignore rules: replace `event_dispatcher` references with `outbox` module references.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(di): wire outbox into API and scheduler, add publisher isolation rules"
```

---

### Task 10: Fix Remaining Tests

**Files:** Various test files that reference old `EventDispatcher`, `JobTriggeredHandler`, or old service constructors.

- [ ] **Step 1: Run full test suite and capture failures**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v --tb=short 2>&1 | tail -40`

- [ ] **Step 2: Fix each failing test**

For each failure:
- Tests that construct services with `EventDispatcher` → replace with `MagicMock()` for `outbox_repo` and `EventSerializer()` or `MagicMock()` for `serializer`
- Tests referencing `JobTriggeredHandler` → replace with `CreateJobRunConsumer`
- Tests referencing `get_event_dispatcher` or `get_triggered_handler` → replace with `get_outbox_repo`, `get_event_serializer`
- Integration test → update service wiring and expected response codes (201 → 202 for trigger)

- [ ] **Step 3: Run linter and architecture checks**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

- [ ] **Step 4: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(test): update tests for outbox pattern refactoring"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run complete pre-PR checks**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: All pass.

- [ ] **Step 2: Verify architecture boundaries**

Confirm:
- `outbox_publisher` does not import `api` or `scheduler`
- `api` does not import `outbox_publisher`
- `scheduler` does not import `outbox_publisher`
- Services do not import `EventDispatcher` (only outbox repo + serializer)
- `EventDispatcher` is only used by `OutboxPublisherService`

- [ ] **Step 3: Commit if any remaining fixes**

```bash
git add -A
git commit -m "chore: final cleanup for outbox pattern implementation"
```
