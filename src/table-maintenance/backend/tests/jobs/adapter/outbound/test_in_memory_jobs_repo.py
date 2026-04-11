import secrets
from datetime import UTC, datetime

import pytest
from base import Repository
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.domain import JobNotFoundError, JobStatus, JobType
from jobs.application.domain.model.job import Job
from jobs.application.domain.model.job_id import JobId


def _make_job(
    job_id: str | None = None,
    job_type: JobType = JobType.REWRITE_DATA_FILES,
    status: JobStatus = JobStatus.PENDING,
) -> Job:
    return Job(
        id=JobId(value=job_id or secrets.token_hex(5)),
        job_type=job_type,
        status=status,
        created_at=datetime.now(UTC),
    )


def test_is_subclass_of_repository():
    assert issubclass(InMemoryJobsRepo, Repository)


def test_create_stores_and_returns_job():
    repo = InMemoryJobsRepo()
    job = _make_job(job_id="abc1234567")
    result = repo.create(job)
    assert result == job
    assert repo.get(JobId(value="abc1234567")) == job


def test_list_all_empty():
    repo = InMemoryJobsRepo()
    assert repo.list_all() == []


def test_list_all_returns_created_jobs():
    repo = InMemoryJobsRepo()
    repo.create(_make_job())
    repo.create(_make_job())
    assert len(repo.list_all()) == 2


def test_get_returns_created_job():
    repo = InMemoryJobsRepo()
    job = _make_job(job_id="abc1234567")
    repo.create(job)
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched == job


def test_get_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get(JobId(value="nonexistent"))
    assert exc_info.value.name == "nonexistent"


def test_delete_removes_job():
    repo = InMemoryJobsRepo()
    job = _make_job(job_id="abc1234567")
    repo.create(job)
    repo.delete(JobId(value="abc1234567"))
    assert repo.list_all() == []


def test_delete_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError):
        repo.delete(JobId(value="nonexistent"))
