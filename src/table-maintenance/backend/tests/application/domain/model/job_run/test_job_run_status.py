"""Tests for JobRunStatus."""

from application.domain.model.job_run import JobRunStatus


def test_enum_values():
    """Verify that all JobRunStatus members have the expected string values."""
    assert JobRunStatus.PENDING == "pending"
    assert JobRunStatus.RUNNING == "running"
    assert JobRunStatus.COMPLETED == "completed"
    assert JobRunStatus.FAILED == "failed"
    assert JobRunStatus.UNKNOWN == "unknown"
