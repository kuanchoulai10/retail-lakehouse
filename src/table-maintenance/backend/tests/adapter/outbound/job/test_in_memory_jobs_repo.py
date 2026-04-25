"""Tests for JobsInMemoryRepo."""

import secrets
from datetime import UTC, datetime

import pytest
from core.base import Repository
from core.adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from core.application.domain import JobNotFoundError, JobType
from core.application.domain.model.job import CronExpression, Job, JobId, JobStatus


def _make_job(
    job_id: str | None = None,
    job_type: JobType = JobType.REWRITE_DATA_FILES,
    status: JobStatus = JobStatus.PAUSED,
) -> Job:
    """Provide a sample Job entity with optional overrides."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id or secrets.token_hex(5)),
        job_type=job_type,
        created_at=now,
        updated_at=now,
        status=status,
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
    original = _make_job(job_id="abc1234567", status=JobStatus.PAUSED)
    repo.create(original)

    modified = _make_job(job_id="abc1234567", status=JobStatus.ACTIVE)
    result = repo.update(modified)

    assert result == modified
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched.status == JobStatus.ACTIVE


def test_update_raises_not_found():
    """Verify that update raises JobNotFoundError for a missing id."""
    repo = JobsInMemoryRepo()
    missing = _make_job(job_id="ghost")
    with pytest.raises(JobNotFoundError):
        repo.update(missing)


def test_list_schedulable_returns_due_enabled_jobs():
    """Verify that list_schedulable returns enabled jobs with cron and next_run_at <= now."""
    repo = JobsInMemoryRepo()
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_job(job_id="j1", status=JobStatus.ACTIVE)
    job.cron = CronExpression(expression="0 * * * *")
    job.next_run_at = datetime(2026, 4, 22, 9, 0, tzinfo=UTC)  # in the past
    repo.create(job)
    result = repo.list_schedulable(now)
    assert len(result) == 1
    assert result[0].id.value == "j1"


def test_list_schedulable_ignores_paused_jobs():
    """Verify that list_schedulable skips paused jobs."""
    repo = JobsInMemoryRepo()
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_job(job_id="j1", status=JobStatus.PAUSED)
    job.cron = CronExpression(expression="0 * * * *")
    job.next_run_at = datetime(2026, 4, 22, 9, 0, tzinfo=UTC)
    repo.create(job)
    assert repo.list_schedulable(now) == []


def test_list_schedulable_ignores_jobs_without_cron():
    """Verify that list_schedulable skips jobs without a cron expression."""
    repo = JobsInMemoryRepo()
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_job(job_id="j1", status=JobStatus.ACTIVE)
    job.next_run_at = datetime(2026, 4, 22, 9, 0, tzinfo=UTC)
    repo.create(job)
    assert repo.list_schedulable(now) == []


def test_list_schedulable_ignores_future_next_run():
    """Verify that list_schedulable skips jobs whose next_run_at is in the future."""
    repo = JobsInMemoryRepo()
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_job(job_id="j1", status=JobStatus.ACTIVE)
    job.cron = CronExpression(expression="0 * * * *")
    job.next_run_at = datetime(2026, 4, 22, 11, 0, tzinfo=UTC)  # future
    repo.create(job)
    assert repo.list_schedulable(now) == []


def test_save_next_run_at_updates_field():
    """Verify that save_next_run_at updates the job's next_run_at."""
    repo = JobsInMemoryRepo()
    job = _make_job(job_id="j1", status=JobStatus.ACTIVE)
    job.cron = CronExpression(expression="0 * * * *")
    job.next_run_at = datetime(2026, 4, 22, 9, 0, tzinfo=UTC)
    repo.create(job)
    new_time = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    repo.save_next_run_at(JobId("j1"), new_time)
    updated = repo.get(JobId("j1"))
    assert updated.next_run_at == new_time
