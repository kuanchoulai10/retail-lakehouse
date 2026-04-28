"""Define the FailJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.domain.model.job_run.job_run_result import JobRunResult
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunUseCaseInput,
    FailJobRunUseCaseOutput,
    FailJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class FailJobRunService(FailJobRunUseCase):
    """Mark a job run as failed with error details."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: FailJobRunUseCaseInput) -> FailJobRunUseCaseOutput:
        """Fail a job run and persist the error."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        result = None
        if request.duration_ms is not None or request.metadata is not None:
            result = JobRunResult(
                duration_ms=request.duration_ms,
                metadata=request.metadata or {},
            )
        finished_at = datetime.now(UTC)
        run.mark_failed(finished_at=finished_at, error=request.error, result=result)
        self._repo.save(run)
        return FailJobRunUseCaseOutput(
            run_id=run.id.value,
            status=run.status.value,
            finished_at=finished_at,
        )
