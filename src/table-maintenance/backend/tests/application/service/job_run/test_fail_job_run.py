"""Tests for FailJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.domain.model.job_run.job_run_result import JobRunResult
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunOutput,
    FailJobRunUseCase,
)
from application.service.job_run.fail_job_run import FailJobRunService
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo


def _running_job_run(run_id: str = "run-1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestFailJobRunService:
    def test_implements_use_case_interface(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = FailJobRunService(repo)
        assert isinstance(service, FailJobRunUseCase)

    def test_fails_running_job_run_with_error(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = FailJobRunService(repo)

        result = service.execute(
            FailJobRunInput(
                run_id="run-1",
                error="Spark OOM",
                duration_ms=500,
                metadata={"stage": "execution"},
            )
        )

        assert isinstance(result, FailJobRunOutput)
        assert result.run_id == "run-1"
        assert result.status == "failed"
        assert result.finished_at is not None

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.status == JobRunStatus.FAILED
        assert saved.error == "Spark OOM"
        assert saved.result == JobRunResult(
            duration_ms=500, metadata={"stage": "execution"}
        )

    def test_fails_with_no_result_metadata(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = FailJobRunService(repo)

        service.execute(
            FailJobRunInput(
                run_id="run-1",
                error="Connection refused",
                duration_ms=None,
                metadata=None,
            )
        )

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.error == "Connection refused"
        assert saved.result is None

    def test_fails_pending_job_run(self) -> None:
        """PENDING -> FAILED is allowed (e.g. submit failure)."""
        repo = JobRunsInMemoryRepo()
        run = JobRun(
            id=JobRunId(value="run-1"),
            job_id=JobId(value="job-1"),
            status=JobRunStatus.PENDING,
        )
        repo.create(run)
        service = FailJobRunService(repo)

        result = service.execute(
            FailJobRunInput(
                run_id="run-1", error="Submit failed", duration_ms=None, metadata=None
            )
        )

        assert result.status == "failed"

    def test_raises_on_not_found(self) -> None:
        import pytest

        repo = JobRunsInMemoryRepo()
        service = FailJobRunService(repo)
        with pytest.raises(Exception):
            service.execute(
                FailJobRunInput(
                    run_id="nope", error="err", duration_ms=None, metadata=None
                )
            )
