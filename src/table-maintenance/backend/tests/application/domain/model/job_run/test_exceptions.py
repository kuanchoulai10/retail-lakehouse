"""Tests for JobRunNotFoundError."""

import pytest

from core.application.domain.model.job_run import JobRunNotFoundError


def test_job_run_not_found_error_stores_run_id():
    """Verify that the error stores the run id and includes it in the message."""
    err = JobRunNotFoundError("run-abc")
    assert err.run_id == "run-abc"
    assert "run-abc" in str(err)


def test_job_run_not_found_error_is_exception():
    """Verify that JobRunNotFoundError can be raised and caught."""
    with pytest.raises(JobRunNotFoundError):
        raise JobRunNotFoundError("x")
