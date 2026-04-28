"""Tests for ListJobRunsService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.service.job_run.list_job_runs import ListJobRunsService
from application.port.inbound import (
    ListJobRunsUseCaseInput,
    ListJobRunsUseCaseOutput,
    ListJobRunsUseCase,
)


def _run(run_id: str, job_id: str = "job-1") -> JobRun:
    """Provide a running JobRun for the given run and job IDs."""
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value=job_id),
        status=JobRunStatus.RUNNING,
        started_at=datetime.now(UTC),
    )


def test_implements_use_case():
    """Verify that ListJobRunsService implements ListJobRunsUseCase."""
    assert issubclass(ListJobRunsService, ListJobRunsUseCase)


def test_list_job_runs_returns_items():
    """Verify that execute returns a ListJobRunsUseCaseOutput with all runs for a job."""
    repo = MagicMock()
    repo.list_for_job.return_value = [_run("a"), _run("b")]
    service = ListJobRunsService(repo)

    result = service.execute(ListJobRunsUseCaseInput(job_id="job-1"))

    assert isinstance(result, ListJobRunsUseCaseOutput)
    assert {r.run_id for r in result.runs} == {"a", "b"}
    repo.list_for_job.assert_called_once_with(JobId(value="job-1"))


def test_list_job_runs_empty():
    """Verify that execute returns an empty list when no runs exist."""
    repo = MagicMock()
    repo.list_for_job.return_value = []
    service = ListJobRunsService(repo)

    assert service.execute(ListJobRunsUseCaseInput(job_id="job-1")).runs == []
