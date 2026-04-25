"""Tests for JobsRepo."""

import pytest
from core.application.domain import JobNotFoundError
from core.application.port.outbound.job.jobs_repo import JobsRepo


def test_job_not_found_error_has_name():
    """Verify that JobNotFoundError stores the job name and includes it in str."""
    err = JobNotFoundError("my-job")
    assert err.name == "my-job"
    assert "my-job" in str(err)


def test_job_not_found_error_is_exception():
    """Verify that JobNotFoundError can be raised and caught."""
    with pytest.raises(JobNotFoundError):
        raise JobNotFoundError("x")


def test_jobs_repo_cannot_be_instantiated():
    """Verify that JobsRepo cannot be instantiated directly as it is abstract."""
    with pytest.raises(TypeError):
        JobsRepo()  # type: ignore[abstract]


def test_jobs_repo_has_abstract_methods():
    """Verify that JobsRepo declares create, list_all, get, delete, and update as abstract."""
    assert "create" in JobsRepo.__abstractmethods__
    assert "list_all" in JobsRepo.__abstractmethods__
    assert "get" in JobsRepo.__abstractmethods__
    assert "delete" in JobsRepo.__abstractmethods__
    assert "update" in JobsRepo.__abstractmethods__


def test_jobs_repo_has_list_schedulable():
    """Verify that JobsRepo declares list_schedulable as abstract."""
    assert "list_schedulable" in JobsRepo.__abstractmethods__


def test_jobs_repo_has_save_next_run_at():
    """Verify that JobsRepo declares save_next_run_at as abstract."""
    assert "save_next_run_at" in JobsRepo.__abstractmethods__
