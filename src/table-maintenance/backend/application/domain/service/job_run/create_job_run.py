"""Define the CreateJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobId, JobNotFoundError
from application.exceptions import JobDisabledError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    CreateJobRunInput,
    CreateJobRunOutput,
    CreateJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_run_executor import JobRunExecutor
    from application.port.outbound.job.jobs_repo import JobsRepo


class CreateJobRunService(CreateJobRunUseCase):
    """Triggers a JobRun via the executor — only if the Job is enabled."""

    def __init__(self, repo: JobsRepo, executor: JobRunExecutor) -> None:
        """Initialize with the jobs repository and job run executor."""
        self._repo = repo
        self._executor = executor

    def execute(self, request: CreateJobRunInput) -> CreateJobRunOutput:
        """Trigger a new execution of the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        if not job.enabled:
            raise JobDisabledError(request.job_id)

        run = self._executor.trigger(job)
        return CreateJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
