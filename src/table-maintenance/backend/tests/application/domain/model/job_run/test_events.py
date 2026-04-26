"""Tests for JobRun domain events."""

from datetime import UTC, datetime

from base import DomainEvent
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
