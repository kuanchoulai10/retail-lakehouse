"""Tests for EventSerializer."""

import json

from application.domain.model.job import (
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job.events import JobCreated, JobPaused, JobTriggered
from application.domain.model.job_run import TriggerType
from application.domain.model.outbox_entry import OutboxEntry
from application.service.outbox.event_serializer import EventSerializer


def _make_serializer() -> EventSerializer:
    return EventSerializer()


def _make_job_triggered(**overrides) -> JobTriggered:
    defaults = {
        "job_id": JobId(value="j1"),
        "trigger_type": TriggerType.MANUAL,
        "job_type": JobType.EXPIRE_SNAPSHOTS,
        "table_ref": TableReference(catalog="cat", table="tbl"),
        "job_config": {},
        "resource_config": ResourceConfig(),
        "cron": None,
    }
    defaults.update(overrides)
    return JobTriggered(**defaults)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


class TestSerialize:
    """Tests for EventSerializer.serialize()."""

    def test_serialize_job_triggered(self):
        """Verify JobTriggered serializes to JSON string."""
        s = _make_serializer()
        event = _make_job_triggered()
        result = s.serialize(event)
        data = json.loads(result)
        assert data["job_id"] == "j1"
        assert data["trigger_type"] == "manual"
        assert data["job_type"] == "expire_snapshots"
        assert data["resource_config"]["driver_memory"] == "512m"

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
        original = _make_job_triggered(trigger_type=TriggerType.SCHEDULED)
        payload = s.serialize(original)
        restored = s.deserialize("JobTriggered", payload)
        assert isinstance(restored, JobTriggered)
        assert restored.job_id == JobId(value="j1")
        assert restored.trigger_type == TriggerType.SCHEDULED
        assert restored.resource_config == ResourceConfig()

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
        events = [_make_job_triggered()]
        entries = s.to_outbox_entries(events, aggregate_type="Job", aggregate_id="j1")
        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, OutboxEntry)
        assert entry.aggregate_type == "Job"
        assert entry.aggregate_id == "j1"
        assert entry.event_type == "JobTriggered"
        assert entry.published_at is None
        assert entry.id

    def test_multiple_events(self):
        """Verify multiple events produce multiple entries."""
        s = _make_serializer()
        events = [
            JobPaused(job_id=JobId(value="j1")),
            _make_job_triggered(),
        ]
        entries = s.to_outbox_entries(events, aggregate_type="Job", aggregate_id="j1")
        assert len(entries) == 2
        assert entries[0].event_type == "JobPaused"
        assert entries[1].event_type == "JobTriggered"
