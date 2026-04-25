"""Tests for job_run_to_values."""

from __future__ import annotations

from datetime import UTC, datetime

from adapter.outbound.job_run.sql.job_run_to_values import job_run_to_values
from core.application.domain.model.job import JobId
from core.application.domain.model.job_run import JobRun, JobRunId, JobRunStatus


def test_serializes_all_fields():
    """Verify that all fields are serialized to the expected dict."""
    run = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        finished_at=None,
    )
    values = job_run_to_values(run)
    assert values == {
        "id": "run-1",
        "job_id": "job-1",
        "status": "running",
        "trigger_type": "manual",
        "started_at": datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        "finished_at": None,
    }


def test_serializes_completed_run_with_finished_at():
    """Verify that a completed run includes the finished_at timestamp."""
    run = JobRun(
        id=JobRunId(value="run-2"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.COMPLETED,
        started_at=datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 4, 10, 13, 0, tzinfo=UTC),
    )
    values = job_run_to_values(run)
    assert values["status"] == "completed"
    assert values["finished_at"] == datetime(2026, 4, 10, 13, 0, tzinfo=UTC)
