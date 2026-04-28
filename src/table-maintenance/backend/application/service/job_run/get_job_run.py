"""Define the GetJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound import (
    GetJobRunInput,
    GetJobRunOutput,
    GetJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class GetJobRunService(GetJobRunUseCase):
    """Retrieves a single JobRun by id."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: GetJobRunInput) -> GetJobRunOutput:
        """Retrieve a job run by its identifier."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        return GetJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            trigger_type=run.trigger_type.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error=run.error,
            result_duration_ms=run.result.duration_ms if run.result else None,
            result_metadata=run.result.metadata if run.result else None,
        )
