import pytest
from application.domain import JobNotFoundError
from application.port.outbound.job.jobs_repo import JobsRepo


def test_job_not_found_error_has_name():
    err = JobNotFoundError("my-job")
    assert err.name == "my-job"
    assert "my-job" in str(err)


def test_job_not_found_error_is_exception():
    with pytest.raises(JobNotFoundError):
        raise JobNotFoundError("x")


def test_jobs_repo_cannot_be_instantiated():
    with pytest.raises(TypeError):
        JobsRepo()  # type: ignore[abstract]


def test_jobs_repo_has_abstract_methods():
    assert "create" in JobsRepo.__abstractmethods__
    assert "list_all" in JobsRepo.__abstractmethods__
    assert "get" in JobsRepo.__abstractmethods__
    assert "delete" in JobsRepo.__abstractmethods__
    assert "update" in JobsRepo.__abstractmethods__
