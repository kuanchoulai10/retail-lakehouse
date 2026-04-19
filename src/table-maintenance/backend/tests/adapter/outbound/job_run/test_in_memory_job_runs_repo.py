"""Tests for JobRunsInMemoryRepo."""

import pytest

from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from application.domain.model.job import JobId
from application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunNotFoundError,
    JobRunStatus,
)
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


def _make_run(run_id: str = "run-1", job_id: str = "job-1") -> JobRun:
    """Provide a sample JobRun entity."""
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value=job_id),
        status=JobRunStatus.PENDING,
    )


def test_is_subclass_of_base_job_runs_repo():
    """Verify that JobRunsInMemoryRepo is a subclass of JobRunsRepo."""
    assert issubclass(JobRunsInMemoryRepo, JobRunsRepo)


def test_get_returns_stored_run():
    """Verify that get returns a previously stored run."""
    repo = JobRunsInMemoryRepo()
    run = _make_run()
    repo.create(run)
    fetched = repo.get(JobRunId(value="run-1"))
    assert fetched == run


def test_get_raises_not_found():
    """Verify that get raises JobRunNotFoundError for a missing id."""
    repo = JobRunsInMemoryRepo()
    with pytest.raises(JobRunNotFoundError) as exc_info:
        repo.get(JobRunId(value="missing"))
    assert exc_info.value.run_id == "missing"


def test_list_for_job_returns_only_matching_runs():
    """Verify that list_for_job returns only runs for the given job."""
    repo = JobRunsInMemoryRepo()
    repo.create(_make_run("run-1", "job-1"))
    repo.create(_make_run("run-2", "job-1"))
    repo.create(_make_run("run-3", "job-2"))
    runs = repo.list_for_job(JobId(value="job-1"))
    assert len(runs) == 2
    assert {r.id.value for r in runs} == {"run-1", "run-2"}


def test_list_all_returns_every_run():
    """Verify that list_all returns every stored run."""
    repo = JobRunsInMemoryRepo()
    repo.create(_make_run("run-1", "job-1"))
    repo.create(_make_run("run-2", "job-2"))
    assert len(repo.list_all()) == 2
