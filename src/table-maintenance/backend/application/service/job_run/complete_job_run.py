"""Define the CompleteJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.domain.model.job_run.job_run_result import JobRunResult
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunOutput,
    CompleteJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CompleteJobRunService(CompleteJobRunUseCase):
    """Mark a running job run as completed with result metadata."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: CompleteJobRunInput) -> CompleteJobRunOutput:
        """Complete a job run and persist the result."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        result = JobRunResult(
            duration_ms=request.duration_ms,
            metadata=request.metadata,
        )
        finished_at = datetime.now(UTC)
        run.mark_completed(finished_at=finished_at, result=result)
        self._repo.save(run)
        return CompleteJobRunOutput(
            run_id=run.id.value,
            status=run.status.value,
            finished_at=finished_at,
        )
