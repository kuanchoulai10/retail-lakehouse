"""Tests for Job domain events."""

from datetime import datetime

from base import DomainEvent
from core.application.domain.model.job import (
    CronExpression,
    FieldChange,
    JobId,
    JobType,
    TableReference,
)
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
