"""Tests for JobRunInMemoryExecutor."""

from datetime import UTC, datetime

from core.adapter.outbound.job_run.job_run_in_memory_executor import (
    JobRunInMemoryExecutor,
)
from application.domain.model.job import Job, JobId, JobType
from application.domain.model.job_run import JobRunStatus
from application.port.outbound.job_run.job_run_executor import JobRunExecutor


def _make_job(job_id: str = "job-1") -> Job:
    """Provide a sample Job entity."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
    )


def test_is_subclass_of_job_run_executor():
    """Verify that JobRunInMemoryExecutor is a subclass of JobRunExecutor."""
    assert issubclass(JobRunInMemoryExecutor, JobRunExecutor)


def test_trigger_returns_job_run_with_status_pending():
    """Verify that trigger returns a job run with pending status."""
    executor = JobRunInMemoryExecutor()
    run = executor.trigger(_make_job())
    assert run.status == JobRunStatus.PENDING


def test_trigger_links_run_to_job_id():
    """Verify that the triggered run is linked to the correct job id."""
    executor = JobRunInMemoryExecutor()
    run = executor.trigger(_make_job("job-xyz"))
    assert run.job_id.value == "job-xyz"


def test_trigger_records_run_for_later_retrieval():
    """Verify that the triggered run is stored for later retrieval."""
    executor = JobRunInMemoryExecutor()
    run = executor.trigger(_make_job("job-1"))
    assert run in executor.triggered_runs


def test_trigger_sets_started_at():
    """Verify that the triggered run has a non-null started_at timestamp."""
    executor = JobRunInMemoryExecutor()
    run = executor.trigger(_make_job())
    assert run.started_at is not None
