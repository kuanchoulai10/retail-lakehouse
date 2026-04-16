from datetime import UTC, datetime

from adapter.outbound.in_memory_job_run_executor import InMemoryJobRunExecutor
from application.domain.model.job import Job
from application.domain.model.job_id import JobId
from application.domain.model.job_run_status import JobRunStatus
from application.domain.model.job_status import JobStatus
from application.domain.model.job_type import JobType
from application.port.outbound.job_run_executor import JobRunExecutor


def _make_job(job_id: str = "job-1") -> Job:
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


def test_is_subclass_of_job_run_executor():
    assert issubclass(InMemoryJobRunExecutor, JobRunExecutor)


def test_trigger_returns_job_run_with_status_pending():
    executor = InMemoryJobRunExecutor()
    run = executor.trigger(_make_job())
    assert run.status == JobRunStatus.PENDING


def test_trigger_links_run_to_job_id():
    executor = InMemoryJobRunExecutor()
    run = executor.trigger(_make_job("job-xyz"))
    assert run.job_id.value == "job-xyz"


def test_trigger_records_run_for_later_retrieval():
    executor = InMemoryJobRunExecutor()
    run = executor.trigger(_make_job("job-1"))
    assert run in executor.triggered_runs


def test_trigger_sets_started_at():
    executor = InMemoryJobRunExecutor()
    run = executor.trigger(_make_job())
    assert run.started_at is not None
