"""Tests for JobRun."""

from datetime import UTC, datetime

from base import AggregateRoot
from application.domain.model.job import JobId, JobType, ResourceConfig, TableReference
from application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunStatus,
    TriggerType,
)
from application.domain.model.job_run.events import (
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
)
from application.domain.model.job_run.job_run_result import JobRunResult


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


def test_create_factory_returns_run_with_event():
    """Verify JobRun.create() returns a JobRun and registers a JobRunCreated event."""
    started = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    rc = ResourceConfig(driver_memory="2g", executor_memory="4g", executor_instances=2)
    run = JobRun.create(
        id=JobRunId(value="r1"),
        job_id=JobId(value="j1"),
        trigger_type=TriggerType.MANUAL,
        started_at=started,
        job_type=JobType.EXPIRE_SNAPSHOTS,
        table_ref=TableReference(catalog="cat", table="tbl"),
        job_config={"retain_last": 5},
        resource_config=rc,
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
    assert events[0].job_type == JobType.EXPIRE_SNAPSHOTS
    assert events[0].resource_config == rc


def _running_job_run() -> JobRun:
    """Create a RUNNING JobRun for testing transitions."""
    return JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


def test_mark_completed_with_result():
    """Verify mark_completed stores result and emits event with result."""
    run = _running_job_run()
    result = JobRunResult(duration_ms=1500, metadata={"expired_snapshots": "42"})
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_completed(finished_at=finished, result=result)

    assert run.status == JobRunStatus.COMPLETED
    assert run.finished_at == finished
    assert run.result == result
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobRunCompleted)
    assert events[0].result == result


def test_mark_failed_with_error_and_result():
    """Verify mark_failed stores error, result, and emits event."""
    run = _running_job_run()
    result = JobRunResult(duration_ms=500, metadata={})
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_failed(finished_at=finished, error="Spark OOM", result=result)

    assert run.status == JobRunStatus.FAILED
    assert run.finished_at == finished
    assert run.result == result
    assert run.error == "Spark OOM"
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobRunFailed)
    assert events[0].error == "Spark OOM"
    assert events[0].result == result


def test_mark_failed_without_result():
    """Verify mark_failed works with result=None."""
    run = _running_job_run()
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_failed(finished_at=finished, error="Connection refused")

    assert run.status == JobRunStatus.FAILED
    assert run.error == "Connection refused"
    assert run.result is None


def test_result_defaults_to_none():
    """Verify result and error default to None on new JobRun."""
    run = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.PENDING,
    )
    assert run.result is None
    assert run.error is None
