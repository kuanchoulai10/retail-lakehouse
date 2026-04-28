"""Tests for CompleteJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.domain.model.job_run.job_run_result import JobRunResult
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunUseCaseInput,
    CompleteJobRunUseCaseOutput,
    CompleteJobRunUseCase,
)
from application.service.job_run.complete_job_run import CompleteJobRunService
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo


def _running_job_run(run_id: str = "run-1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestCompleteJobRunService:
    def test_implements_use_case_interface(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = CompleteJobRunService(repo)
        assert isinstance(service, CompleteJobRunUseCase)

    def test_completes_running_job_run(self) -> None:
        repo = JobRunsInMemoryRepo()
        run = _running_job_run()
        repo.create(run)
        service = CompleteJobRunService(repo)

        result = service.execute(
            CompleteJobRunUseCaseInput(
                run_id="run-1",
                duration_ms=1500,
                metadata={"expired_snapshots": "42"},
            )
        )

        assert isinstance(result, CompleteJobRunUseCaseOutput)
        assert result.run_id == "run-1"
        assert result.status == "completed"
        assert result.finished_at is not None

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.status == JobRunStatus.COMPLETED
        assert saved.result == JobRunResult(
            duration_ms=1500, metadata={"expired_snapshots": "42"}
        )

    def test_completes_with_none_duration(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = CompleteJobRunService(repo)

        service.execute(
            CompleteJobRunUseCaseInput(run_id="run-1", duration_ms=None, metadata={})
        )

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.result == JobRunResult(duration_ms=None, metadata={})

    def test_raises_on_not_found(self) -> None:
        import pytest

        repo = JobRunsInMemoryRepo()
        service = CompleteJobRunService(repo)
        with pytest.raises(Exception):
            service.execute(
                CompleteJobRunUseCaseInput(run_id="nope", duration_ms=None, metadata={})
            )

    def test_raises_on_invalid_transition(self) -> None:
        import pytest

        repo = JobRunsInMemoryRepo()
        run = JobRun(
            id=JobRunId(value="run-1"),
            job_id=JobId(value="job-1"),
            status=JobRunStatus.PENDING,
        )
        repo.create(run)
        service = CompleteJobRunService(repo)
        with pytest.raises(Exception):
            service.execute(
                CompleteJobRunUseCaseInput(
                    run_id="run-1", duration_ms=None, metadata={}
                )
            )
