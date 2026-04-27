"""Tests for SubmitJobRunInMemoryGateway."""

from adapter.outbound.job_run.submit_job_run_in_memory_gateway import (
    SubmitJobRunInMemoryGateway,
)
from application.port.outbound.job_run.submit_job_run_gateway import SubmitJobRunGateway
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


def test_is_subclass_of_gateway():
    """Verify that SubmitJobRunInMemoryGateway is a subclass of SubmitJobRunGateway."""
    assert issubclass(SubmitJobRunInMemoryGateway, SubmitJobRunGateway)


def test_submit_records_submission():
    """Verify that submit records the submission."""
    gateway = SubmitJobRunInMemoryGateway()
    sub = _submission()
    gateway.submit(sub)
    assert sub in gateway.submitted


def test_submit_returns_none():
    """Verify that submit returns None."""
    gateway = SubmitJobRunInMemoryGateway()
    result = gateway.submit(_submission())
    assert result is None
