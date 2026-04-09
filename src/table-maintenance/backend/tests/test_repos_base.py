import pytest
from repos.base_jobs_repo import BaseJobsRepo
from repos.exceptions import JobNotFoundError


def test_job_not_found_error_has_name():
    err = JobNotFoundError("my-job")
    assert err.name == "my-job"
    assert "my-job" in str(err)


def test_job_not_found_error_is_exception():
    with pytest.raises(JobNotFoundError):
        raise JobNotFoundError("x")


def test_jobs_repo_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseJobsRepo()  # type: ignore[abstract]


def test_jobs_repo_has_abstract_methods():
    assert "create" in BaseJobsRepo.__abstractmethods__
    assert "list_all" in BaseJobsRepo.__abstractmethods__
    assert "get" in BaseJobsRepo.__abstractmethods__
    assert "delete" in BaseJobsRepo.__abstractmethods__
