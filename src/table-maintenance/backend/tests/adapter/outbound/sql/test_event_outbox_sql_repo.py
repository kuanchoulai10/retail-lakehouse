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
        id="e1",
        aggregate_type="Job",
        aggregate_id="j1",
        event_type="JobCreated",
        payload="{}",
        occurred_at=datetime(2026, 4, 25, 10, 0, tzinfo=UTC),
    )
    late = OutboxEntry(
        id="e2",
        aggregate_type="Job",
        aggregate_id="j1",
        event_type="JobTriggered",
        payload="{}",
        occurred_at=datetime(2026, 4, 25, 14, 0, tzinfo=UTC),
    )
    repo.save([late, early])
    result = repo.fetch_unpublished()
    assert result[0].id == "e1"
    assert result[1].id == "e2"
