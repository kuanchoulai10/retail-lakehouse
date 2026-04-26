"""Tests for OutboxEntry value object."""

from datetime import UTC, datetime

from base import ValueObject
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
