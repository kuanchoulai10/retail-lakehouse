"""Tests for JobRunInMemoryExecutor."""

from adapter.outbound.job_run.job_run_in_memory_executor import (
    JobRunInMemoryExecutor,
)
from application.port.outbound.job_run.job_run_executor import JobRunExecutor
from application.port.outbound.job_run.job_submission import JobSubmission


def _submission(**overrides) -> JobSubmission:
    defaults = {
        "run_id": "r1",
        "job_id": "j1",
        "job_type": "expire_snapshots",
        "catalog": "retail",
        "table": "orders",
        "job_config": {},
        "driver_memory": "512m",
        "executor_memory": "1g",
        "executor_instances": 1,
        "cron_expression": None,
    }
    defaults.update(overrides)
    return JobSubmission(**defaults)  # type: ignore[arg-type]


def test_is_subclass_of_job_run_executor():
    """Verify that JobRunInMemoryExecutor is a subclass of JobRunExecutor."""
    assert issubclass(JobRunInMemoryExecutor, JobRunExecutor)


def test_submit_records_submission():
    """Verify that submit records the submission."""
    executor = JobRunInMemoryExecutor()
    sub = _submission()
    executor.submit(sub)
    assert sub in executor.submitted


def test_submit_returns_none():
    """Verify that submit returns None."""
    executor = JobRunInMemoryExecutor()
    result = executor.submit(_submission())
    assert result is None
