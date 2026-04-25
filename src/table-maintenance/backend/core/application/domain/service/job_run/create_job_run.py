"""Define the CreateJobRunService."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job import (
    JobId,
    JobNotActiveError,
    JobNotFoundError,
    MaxActiveRunsExceededError,
)
from core.application.domain.model.job_run import JobRunId
from core.application.exceptions import JobDisabledError
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    CreateJobRunInput,
    CreateJobRunOutput,
    CreateJobRunUseCase,
)

if TYPE_CHECKING:
    from core.application.port.outbound.job.jobs_repo import JobsRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CreateJobRunService(CreateJobRunUseCase):
    """Triggers a JobRun via Job.trigger() — only if the Job is active."""

    def __init__(self, repo: JobsRepo, job_runs_repo: JobRunsRepo) -> None:
        """Initialize with the jobs and job runs repositories."""
        self._repo = repo
        self._job_runs_repo = job_runs_repo

    def execute(self, request: CreateJobRunInput) -> CreateJobRunOutput:
        """Trigger a new execution of the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        active_count = self._job_runs_repo.count_active_for_job(job.id)

        try:
            run = job.trigger(
                run_id=JobRunId(value=f"{job.id.value}-{secrets.token_hex(3)}"),
                now=datetime.now(UTC),
                active_run_count=active_count,
            )
        except JobNotActiveError as e:
            raise JobDisabledError(e.job_id) from e
        except MaxActiveRunsExceededError as e:
            raise JobDisabledError(e.job_id) from e

        run = self._job_runs_repo.create(run)
        return CreateJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            trigger_type=run.trigger_type.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
