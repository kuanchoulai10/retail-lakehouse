import pytest
from jobs.adapter.inbound.web.dto import JobApiRequest
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
from jobs.domain import JobNotFoundError, JobStatus, JobType


def _make_request(
    job_type: str = "rewrite_data_files",
    cron: str | None = None,
) -> JobApiRequest:
    return JobApiRequest(
        job_type=job_type,
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
        cron=cron,
    )


def test_is_subclass_of_jobs_repo():
    repo = InMemoryJobsRepo()
    assert isinstance(repo, BaseJobsRepo)


def test_create_returns_job_with_id():
    repo = InMemoryJobsRepo()
    job = repo.create(_make_request())
    assert len(job.id.value) == 10  # secrets.token_hex(5) produces 10 hex chars
    assert job.job_type == JobType.REWRITE_DATA_FILES
    assert job.status == JobStatus.PENDING


def test_create_scheduled_sets_running_status():
    repo = InMemoryJobsRepo()
    job = repo.create(_make_request(cron="0 2 * * *"))
    assert job.status == JobStatus.RUNNING


def test_list_all_empty():
    repo = InMemoryJobsRepo()
    assert repo.list_all() == []


def test_list_all_returns_created_jobs():
    repo = InMemoryJobsRepo()
    repo.create(_make_request())
    repo.create(_make_request())
    assert len(repo.list_all()) == 2


def test_get_returns_created_job():
    repo = InMemoryJobsRepo()
    created = repo.create(_make_request())
    fetched = repo.get(created.id.value)
    assert fetched.id.value == created.id.value


def test_get_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.name == "nonexistent"


def test_delete_removes_job():
    repo = InMemoryJobsRepo()
    created = repo.create(_make_request())
    repo.delete(created.id.value)
    assert repo.list_all() == []


def test_delete_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError):
        repo.delete("nonexistent")
