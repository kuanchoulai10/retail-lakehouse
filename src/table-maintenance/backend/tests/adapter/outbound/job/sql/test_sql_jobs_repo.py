from datetime import UTC, datetime

import pytest

from adapter.outbound.job.sql.sql_jobs_repo import SqlJobsRepo
from application.domain.model.job import Job, JobId, JobNotFoundError, JobType
from application.port.outbound.job.jobs_repo import BaseJobsRepo


def _make_job(
    job_id: str = "abc1234567",
    enabled: bool = False,
    cron: str | None = None,
) -> Job:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        catalog="retail",
        table="inventory.orders",
        job_config={"rewrite_all": True},
        cron=cron,
        enabled=enabled,
    )


def test_is_subclass_of_base_jobs_repo(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    assert isinstance(repo, BaseJobsRepo)


def test_create_inserts_row(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    job = _make_job()
    result = repo.create(job)
    assert result == job


def test_get_returns_created_job(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    job = _make_job("abc1234567")
    repo.create(job)
    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched == job


def test_get_raises_not_found(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get(JobId(value="missing"))
    assert exc_info.value.name == "missing"


def test_list_all_returns_all_jobs(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    repo.create(_make_job("a"))
    repo.create(_make_job("b"))
    jobs = repo.list_all()
    assert {j.id.value for j in jobs} == {"a", "b"}


def test_list_all_empty(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    assert repo.list_all() == []


def test_delete_removes_job(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    repo.create(_make_job("abc1234567"))
    repo.delete(JobId(value="abc1234567"))
    assert repo.list_all() == []


def test_delete_raises_not_found(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError):
        repo.delete(JobId(value="missing"))


def test_update_replaces_row(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    original = _make_job("abc1234567", enabled=False)
    repo.create(original)

    modified = _make_job("abc1234567", enabled=True)
    repo.update(modified)

    fetched = repo.get(JobId(value="abc1234567"))
    assert fetched.enabled is True


def test_update_raises_not_found(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    with pytest.raises(JobNotFoundError):
        repo.update(_make_job("ghost"))


def test_enabled_roundtrips(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    repo.create(_make_job("a", enabled=True))
    repo.create(_make_job("b", enabled=False))
    jobs = {j.id.value: j for j in repo.list_all()}
    assert jobs["a"].enabled is True
    assert jobs["b"].enabled is False


def test_cron_nullable_roundtrips(sqlite_engine):
    repo = SqlJobsRepo(sqlite_engine)
    repo.create(_make_job("a", cron=None))
    repo.create(_make_job("b", cron="0 2 * * *"))
    jobs = {j.id.value: j for j in repo.list_all()}
    assert jobs["a"].cron is None
    assert jobs["b"].cron == "0 2 * * *"
