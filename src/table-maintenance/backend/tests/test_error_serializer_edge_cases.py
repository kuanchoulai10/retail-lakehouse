"""Tests for EventSerializer edge cases and boundary conditions."""

from __future__ import annotations

import pytest

from application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job.events import JobTriggered
from application.domain.model.job_run import JobRunId, TriggerType
from application.domain.model.job_run.events import JobRunCreated
from application.service.outbox.event_serializer import EventSerializer


def _serializer() -> EventSerializer:
    return EventSerializer()


def test_roundtrip_job_triggered_with_empty_job_config():
    """Verify empty job_config survives serialize/deserialize."""
    s = _serializer()
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.REWRITE_DATA_FILES,
        table_ref=TableReference(catalog="c", table="t"),
        job_config={},
        resource_config=ResourceConfig(),
        cron=None,
    )
    payload = s.serialize(event)
    restored = s.deserialize("JobTriggered", payload)
    assert isinstance(restored, JobTriggered)
    assert restored.job_config == {}


def test_roundtrip_job_triggered_with_large_job_config():
    """Verify a 100-key job_config dict round-trips correctly."""
    s = _serializer()
    large_config = {f"key_{i}": f"value_{i}" for i in range(100)}
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="c", table="t"),
        job_config=large_config,
        resource_config=ResourceConfig(),
        cron=None,
    )
    payload = s.serialize(event)
    restored = s.deserialize("JobTriggered", payload)
    assert isinstance(restored, JobTriggered)
    assert restored.job_config == large_config


def test_roundtrip_job_triggered_with_special_chars():
    """Verify special characters in job_config survive round-trip."""
    s = _serializer()
    special_config = {
        "chinese": "資料表維護",
        "backslash": "path\\to\\file",
        "quotes": 'say "hello"',
        "newline": "line1\nline2",
    }
    event = JobTriggered(
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
        job_type=JobType.REWRITE_MANIFESTS,
        table_ref=TableReference(catalog="c", table="t"),
        job_config=special_config,
        resource_config=ResourceConfig(),
        cron=None,
    )
    payload = s.serialize(event)
    restored = s.deserialize("JobTriggered", payload)
    assert isinstance(restored, JobTriggered)
    assert restored.job_config == special_config


def test_roundtrip_job_run_created_with_cron_none():
    """Verify cron=None round-trips to None."""
    s = _serializer()
    event = JobRunCreated(
        run_id=JobRunId(value="r1"),
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="c", table="t"),
        job_config={},
        resource_config=ResourceConfig(),
        cron=None,
    )
    payload = s.serialize(event)
    restored = s.deserialize("JobRunCreated", payload)
    assert isinstance(restored, JobRunCreated)
    assert restored.cron is None


def test_roundtrip_job_run_created_with_resource_config():
    """Verify ResourceConfig fields survive round-trip."""
    s = _serializer()
    rc = ResourceConfig(driver_memory="4g", executor_memory="8g", executor_instances=5)
    event = JobRunCreated(
        run_id=JobRunId(value="r1"),
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.SCHEDULED,
        job_type=JobType.REWRITE_DATA_FILES,
        table_ref=TableReference(catalog="retail", table="orders"),
        job_config={"strategy": "sort"},
        resource_config=rc,
        cron=CronExpression(expression="0 3 * * *"),
    )
    payload = s.serialize(event)
    restored = s.deserialize("JobRunCreated", payload)
    assert isinstance(restored, JobRunCreated)
    assert restored.resource_config == rc
    assert restored.cron == CronExpression(expression="0 3 * * *")


def test_deserialize_unknown_event_type_raises():
    """Verify unknown event type raises KeyError."""
    s = _serializer()
    with pytest.raises(KeyError):
        s.deserialize("UnknownEventType", "{}")
