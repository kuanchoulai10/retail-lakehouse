import pytest

from application.domain.model.exceptions import (
    JobNotFoundError,
    JobRunNotFoundError,
)


def test_job_not_found_error_stores_name():
    err = JobNotFoundError("missing-id")
    assert err.name == "missing-id"
    assert "missing-id" in str(err)


def test_job_run_not_found_error_stores_run_id():
    err = JobRunNotFoundError("run-abc")
    assert err.run_id == "run-abc"
    assert "run-abc" in str(err)


def test_job_run_not_found_error_is_exception():
    with pytest.raises(JobRunNotFoundError):
        raise JobRunNotFoundError("x")
