"""Tests for JobNotFoundError."""

from application.domain.model.job import JobNotFoundError


def test_job_not_found_error_stores_name():
    """Verify that the error stores the job name and includes it in the message."""
    err = JobNotFoundError("missing-id")
    assert err.name == "missing-id"
    assert "missing-id" in str(err)
