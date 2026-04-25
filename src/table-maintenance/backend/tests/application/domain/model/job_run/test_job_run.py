"""Tests for JobRun."""

from datetime import UTC, datetime

from core.base import AggregateRoot
from core.application.domain.model.job import JobId
from core.application.domain.model.job_run import JobRun, JobRunId, JobRunStatus


def test_is_aggregate_root():
    """Verify that JobRun is a subclass of AggregateRoot."""
    assert issubclass(JobRun, AggregateRoot)


def test_fields():
    """Verify that all JobRun fields are stored correctly."""
    run_id = JobRunId(value="job-1-abc")
    job_id = JobId(value="job-1")
    started = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobRunStatus.PENDING,
        started_at=started,
        finished_at=None,
    )
    assert run.id == run_id
    assert run.job_id == job_id
    assert run.status == JobRunStatus.PENDING
    assert run.started_at == started
    assert run.finished_at is None


def test_equality_by_id():
    """Verify that two JobRuns with the same id are equal."""
    a = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.PENDING,
        started_at=None,
        finished_at=None,
    )
    b = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-2"),
        status=JobRunStatus.COMPLETED,
        started_at=datetime.now(UTC),
        finished_at=None,
    )
    assert a == b


def test_started_at_defaults_to_none():
    """Verify that started_at and finished_at default to None."""
    run = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.PENDING,
    )
    assert run.started_at is None
    assert run.finished_at is None
