"""Tests for JobsInMemoryRepo."""

import secrets
from datetime import UTC, datetime

import pytest
from base import Repository
from adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from application.domain import JobNotFoundError, JobType
from application.domain.model.job import Job, JobId


def _make_job(
    job_id: str | None = None,
    job_type: JobType = JobType.REWRITE_DATA_FILES,
    enabled: bool = False,
) -> Job:
    """Provide a sample Job entity with optional overrides."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id or secrets.token_hex(5)),
        job_type=job_type,
        created_at=now,
        updated_at=now,
        enabled=enabled,
    )


def test_is_subclass_of_repository():
    """Verify that JobsInMemoryRepo is a subclass of Repository."""
    assert issubclass(JobsInMemoryRepo, Repository)


def test_create_stores_and_returns_job():
    """Verify that create stores the job and returns it."""
    repo = JobsInMemoryRepo()
    job = _make_job(job_id="abc1234567")
    result = repo.create(job)
    assert result == job
    assert repo.get(JobId(value="abc1234567")) == job


def test_list_all_empty():
    """Verify that list_all returns an empty list when no jobs exist."""
    repo = JobsInMemoryRepo()
    assert repo.list_all() == []


def test_list_all_returns_created_jobs():
    """Verify that list_all returns all previously created jobs."""
    repo = JobsInMemoryRepo()
    repo.create(_make_job())
    repo.create(_make_job())
    assert len(repo.list_all()) == 2


def test_get_returns_created_job():
    """Verify that get returns a previously created job by id."""
    repo = JobsInMemoryRepo()
    job = _make_job(job_id="abc1234567")
    repo.create(job)
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched == job


def test_get_raises_not_found():
    """Verify that get raises JobNotFoundError for a missing id."""
    repo = JobsInMemoryRepo()
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get(JobId(value="nonexistent"))
    assert exc_info.value.name == "nonexistent"


def test_delete_removes_job():
    """Verify that delete removes the job from the store."""
    repo = JobsInMemoryRepo()
    job = _make_job(job_id="abc1234567")
    repo.create(job)
    repo.delete(JobId(value="abc1234567"))
    assert repo.list_all() == []


def test_delete_raises_not_found():
    """Verify that delete raises JobNotFoundError for a missing id."""
    repo = JobsInMemoryRepo()
    with pytest.raises(JobNotFoundError):
        repo.delete(JobId(value="nonexistent"))


def test_update_replaces_existing_job():
    """Verify that update replaces the existing job with the new one."""
    repo = JobsInMemoryRepo()
    original = _make_job(job_id="abc1234567", enabled=False)
    repo.create(original)

    modified = _make_job(job_id="abc1234567", enabled=True)
    result = repo.update(modified)

    assert result == modified
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched.enabled is True


def test_update_raises_not_found():
    """Verify that update raises JobNotFoundError for a missing id."""
    repo = JobsInMemoryRepo()
    missing = _make_job(job_id="ghost")
    with pytest.raises(JobNotFoundError):
        repo.update(missing)
