"""Tests for JobsSqlRepo."""

from datetime import UTC, datetime

import pytest

from core.adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobNotFoundError,
    JobStatus,
    JobType,
    TableReference,
)
from application.port.outbound.job.jobs_repo import JobsRepo


def _make_job(
    job_id: str = "abc1234567",
    status: JobStatus = JobStatus.PAUSED,
    cron: str | None = None,
) -> Job:
    """Provide a sample Job entity with optional overrides."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={"rewrite_all": True},
        cron=CronExpression(expression=cron) if cron else None,
        status=status,
    )


def test_is_subclass_of_base_jobs_repo(sqlite_engine):
    """Verify that JobsSqlRepo implements the JobsRepo interface."""
    repo = JobsSqlRepo(sqlite_engine)
    assert isinstance(repo, JobsRepo)


def test_create_inserts_row(sqlite_engine):
    """Verify that create inserts a row and returns the job."""
    repo = JobsSqlRepo(sqlite_engine)
    job = _make_job()
    result = repo.create(job)
    assert result == job


def test_get_returns_created_job(sqlite_engine):
    """Verify that get returns a previously created job."""
    repo = JobsSqlRepo(sqlite_engine)
    job = _make_job("abc1234567")
    repo.create(job)
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched == job


def test_get_raises_not_found(sqlite_engine):
    """Verify that get raises JobNotFoundError for a missing id."""
    repo = JobsSqlRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get(JobId(value="missing"))
    assert exc_info.value.name == "missing"


def test_list_all_returns_all_jobs(sqlite_engine):
    """Verify that list_all returns every stored job."""
    repo = JobsSqlRepo(sqlite_engine)
    repo.create(_make_job("a"))
    repo.create(_make_job("b"))
    jobs = repo.list_all()
    assert {j.id.value for j in jobs} == {"a", "b"}


def test_list_all_empty(sqlite_engine):
    """Verify that list_all returns an empty list when no jobs exist."""
    repo = JobsSqlRepo(sqlite_engine)
    assert repo.list_all() == []


def test_delete_removes_job(sqlite_engine):
    """Verify that delete removes the job from the store."""
    repo = JobsSqlRepo(sqlite_engine)
    repo.create(_make_job("abc1234567"))
    repo.delete(JobId(value="abc1234567"))
    assert repo.list_all() == []


def test_delete_raises_not_found(sqlite_engine):
    """Verify that delete raises JobNotFoundError for a missing id."""
    repo = JobsSqlRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError):
        repo.delete(JobId(value="missing"))


def test_update_replaces_row(sqlite_engine):
    """Verify that update replaces the existing row with new values."""
    repo = JobsSqlRepo(sqlite_engine)
    original = _make_job("abc1234567", status=JobStatus.PAUSED)
    repo.create(original)

    modified = _make_job("abc1234567", status=JobStatus.ACTIVE)
    repo.update(modified)

    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched.status == JobStatus.ACTIVE


def test_update_raises_not_found(sqlite_engine):
    """Verify that update raises JobNotFoundError for a missing id."""
    repo = JobsSqlRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError):
        repo.update(_make_job("ghost"))


def test_status_roundtrips(sqlite_engine):
    """Verify that the status field roundtrips through the database."""
    repo = JobsSqlRepo(sqlite_engine)
    repo.create(_make_job("a", status=JobStatus.ACTIVE))
    repo.create(_make_job("b", status=JobStatus.PAUSED))
    jobs = {j.id.value: j for j in repo.list_all()}
    assert jobs["a"].status == JobStatus.ACTIVE
    assert jobs["b"].status == JobStatus.PAUSED


def test_cron_nullable_roundtrips(sqlite_engine):
    """Verify that nullable cron values roundtrip through the database."""
    repo = JobsSqlRepo(sqlite_engine)
    repo.create(_make_job("a", cron=None))
    repo.create(_make_job("b", cron="0 2 * * *"))
    jobs = {j.id.value: j for j in repo.list_all()}
    assert jobs["a"].cron is None
    assert jobs["b"].cron == CronExpression(expression="0 2 * * *")


def _make_schedulable_job(
    job_id: str,
    next_run_at: datetime,
    status: JobStatus = JobStatus.ACTIVE,
    cron: str = "0 * * * *",
    max_active_runs: int = 1,
) -> Job:
    """Provide a Job entity with scheduling fields set."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        cron=CronExpression(expression=cron),
        status=status,
        next_run_at=next_run_at,
        max_active_runs=max_active_runs,
    )


def test_scheduling_fields_roundtrip(sqlite_engine):
    """Verify that next_run_at and max_active_runs roundtrip through the database."""
    repo = JobsSqlRepo(sqlite_engine)
    run_at = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_schedulable_job("j1", next_run_at=run_at, max_active_runs=3)
    repo.create(job)
    fetched = repo.get(JobId("j1"))
    # SQLite strips timezone info; compare naive part only
    assert fetched.next_run_at is not None
    assert fetched.next_run_at.replace(tzinfo=UTC) == run_at
    assert fetched.max_active_runs == 3


def test_list_schedulable_returns_due_jobs(sqlite_engine):
    """Verify that list_schedulable returns enabled jobs with next_run_at <= now."""
    repo = JobsSqlRepo(sqlite_engine)
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    repo.create(
        _make_schedulable_job("j1", next_run_at=datetime(2026, 4, 22, 9, 0, tzinfo=UTC))
    )
    result = repo.list_schedulable(now)
    assert len(result) == 1
    assert result[0].id.value == "j1"


def test_list_schedulable_skips_paused(sqlite_engine):
    """Verify that list_schedulable skips paused jobs."""
    repo = JobsSqlRepo(sqlite_engine)
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    repo.create(
        _make_schedulable_job(
            "j1",
            next_run_at=datetime(2026, 4, 22, 9, 0, tzinfo=UTC),
            status=JobStatus.PAUSED,
        )
    )
    assert repo.list_schedulable(now) == []


def test_list_schedulable_skips_no_cron(sqlite_engine):
    """Verify that list_schedulable skips jobs without a cron expression."""
    repo = JobsSqlRepo(sqlite_engine)
    now = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    job = _make_job("j1", status=JobStatus.ACTIVE)
    job.next_run_at = datetime(2026, 4, 22, 9, 0, tzinfo=UTC)
    repo.create(job)
    assert repo.list_schedulable(now) == []


def test_save_next_run_at_updates_row(sqlite_engine):
    """Verify that save_next_run_at updates the persisted next_run_at."""
    repo = JobsSqlRepo(sqlite_engine)
    repo.create(
        _make_schedulable_job("j1", next_run_at=datetime(2026, 4, 22, 9, 0, tzinfo=UTC))
    )
    new_time = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    repo.save_next_run_at(JobId("j1"), new_time)
    fetched = repo.get(JobId("j1"))
    # SQLite strips timezone info; compare naive part only
    assert fetched.next_run_at is not None
    assert fetched.next_run_at.replace(tzinfo=UTC) == new_time
