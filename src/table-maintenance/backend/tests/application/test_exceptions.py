"""Tests for application-layer exceptions."""

import pytest

from application.exceptions import JobNotFoundError, JobRunNotFoundError


def test_job_not_found_error_stores_job_id():
    """Verify that JobNotFoundError stores the job id and includes it in the message."""
    err = JobNotFoundError("missing-id")
    assert err.job_id == "missing-id"
    assert "missing-id" in str(err)


def test_job_run_not_found_error_stores_run_id():
    """Verify that JobRunNotFoundError stores the run id and includes it in the message."""
    err = JobRunNotFoundError("run-abc")
    assert err.run_id == "run-abc"
    assert "run-abc" in str(err)


def test_job_run_not_found_error_is_exception():
    """Verify that JobRunNotFoundError can be raised and caught."""
    with pytest.raises(JobRunNotFoundError):
        raise JobRunNotFoundError("x")
