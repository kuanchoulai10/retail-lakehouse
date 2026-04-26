"""Tests for JobRunsSqlRepo."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, insert

from core.adapter.outbound.job.sql.jobs_table import jobs_table
from core.adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from application.domain.model.job import JobId
from application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunNotFoundError,
    JobRunStatus,
)
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

NOW = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)


def _insert_parent_job(engine: Engine, job_id: str) -> None:
    """Insert a parent job row required by the foreign key constraint."""
    with engine.begin() as conn:
        conn.execute(
            insert(jobs_table).values(
                id=job_id,
                job_type="rewrite_data_files",
                catalog="retail",
                table="inventory.orders",
                job_config={},
                cron=None,
                status="active",
                next_run_at=None,
                max_active_runs=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def _make_run(
    run_id: str = "run-1",
    job_id: str = "job-1",
    status: JobRunStatus = JobRunStatus.PENDING,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> JobRun:
    """Provide a sample JobRun entity with optional overrides."""
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value=job_id),
        status=status,
        started_at=started_at,
        finished_at=finished_at,
    )


def test_is_subclass_of_base_job_runs_repo(sqlite_engine):
    """Verify that JobRunsSqlRepo implements the JobRunsRepo interface."""
    repo = JobRunsSqlRepo(sqlite_engine)
    assert isinstance(repo, JobRunsRepo)


def test_create_and_get_roundtrip(sqlite_engine):
    """Verify that a created run can be retrieved by id."""
    _insert_parent_job(sqlite_engine, "job-1")
    repo = JobRunsSqlRepo(sqlite_engine)
    run = _make_run("run-1", "job-1")
    result = repo.create(run)
    assert result == run
    fetched = repo.get(JobRunId(value="run-1"))
    assert fetched == run


def test_get_raises_not_found(sqlite_engine):
    """Verify that get raises JobRunNotFoundError for a missing id."""
    repo = JobRunsSqlRepo(sqlite_engine)
    with pytest.raises(JobRunNotFoundError) as exc_info:
        repo.get(JobRunId(value="missing"))
    assert exc_info.value.run_id == "missing"


def test_list_for_job_filters_correctly(sqlite_engine):
    """Verify that list_for_job returns only runs belonging to the given job."""
    _insert_parent_job(sqlite_engine, "job-1")
    _insert_parent_job(sqlite_engine, "job-2")
    repo = JobRunsSqlRepo(sqlite_engine)
    repo.create(_make_run("run-1", "job-1"))
    repo.create(_make_run("run-2", "job-1"))
    repo.create(_make_run("run-3", "job-2"))
    runs = repo.list_for_job(JobId(value="job-1"))
    assert {r.id.value for r in runs} == {"run-1", "run-2"}


def test_list_for_job_empty_for_unknown_job(sqlite_engine):
    """Verify that list_for_job returns an empty list for an unknown job."""
    repo = JobRunsSqlRepo(sqlite_engine)
    assert repo.list_for_job(JobId(value="no-such-job")) == []


def test_list_all(sqlite_engine):
    """Verify that list_all returns every stored run."""
    _insert_parent_job(sqlite_engine, "job-1")
    _insert_parent_job(sqlite_engine, "job-2")
    repo = JobRunsSqlRepo(sqlite_engine)
    repo.create(_make_run("run-1", "job-1"))
    repo.create(_make_run("run-2", "job-2"))
    assert len(repo.list_all()) == 2


def test_list_all_empty(sqlite_engine):
    """Verify that list_all returns an empty list when no runs exist."""
    repo = JobRunsSqlRepo(sqlite_engine)
    assert repo.list_all() == []


def test_status_roundtrips(sqlite_engine):
    """Verify that all JobRunStatus values roundtrip through the database."""
    _insert_parent_job(sqlite_engine, "job-1")
    repo = JobRunsSqlRepo(sqlite_engine)
    for status in JobRunStatus:
        run_id = f"run-{status.value}"
        repo.create(_make_run(run_id, "job-1", status=status))
    runs = {r.id.value: r for r in repo.list_all()}
    for status in JobRunStatus:
        assert runs[f"run-{status.value}"].status == status


def test_nullable_timestamps_roundtrip(sqlite_engine):
    """Verify that null timestamps roundtrip through the database."""
    _insert_parent_job(sqlite_engine, "job-1")
    repo = JobRunsSqlRepo(sqlite_engine)
    repo.create(_make_run("run-1", "job-1"))
    fetched = repo.get(JobRunId(value="run-1"))
    assert fetched.started_at is None
    assert fetched.finished_at is None


def test_timestamps_roundtrip(sqlite_engine):
    """Verify that non-null timestamps roundtrip through the database."""
    _insert_parent_job(sqlite_engine, "job-1")
    repo = JobRunsSqlRepo(sqlite_engine)
    run = _make_run(
        "run-1",
        "job-1",
        status=JobRunStatus.COMPLETED,
        started_at=datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 4, 10, 13, 0, tzinfo=UTC),
    )
    repo.create(run)
    fetched = repo.get(JobRunId(value="run-1"))
    # SQLite strips timezone info; compare naive part only
    assert fetched.started_at is not None
    assert fetched.finished_at is not None
    assert fetched.started_at.replace(tzinfo=UTC) == run.started_at
    assert fetched.finished_at.replace(tzinfo=UTC) == run.finished_at


def test_count_active_for_job(sqlite_engine):
    """Verify that count_active_for_job counts pending and running runs."""
    _insert_parent_job(sqlite_engine, "job-1")
    repo = JobRunsSqlRepo(sqlite_engine)
    repo.create(_make_run("r1", "job-1", JobRunStatus.PENDING))
    repo.create(_make_run("r2", "job-1", JobRunStatus.RUNNING))
    repo.create(_make_run("r3", "job-1", JobRunStatus.COMPLETED))
    repo.create(_make_run("r4", "job-1", JobRunStatus.FAILED))
    assert repo.count_active_for_job(JobId("job-1")) == 2


def test_count_active_returns_zero_when_empty(sqlite_engine):
    """Verify that count_active_for_job returns 0 when no runs exist."""
    repo = JobRunsSqlRepo(sqlite_engine)
    assert repo.count_active_for_job(JobId("job-1")) == 0
