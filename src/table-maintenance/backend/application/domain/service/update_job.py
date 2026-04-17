from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job import JobId, JobNotFoundError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import UpdateJobInput, UpdateJobOutput, UpdateJobUseCase

if TYPE_CHECKING:
    from application.port.outbound.jobs_repo import BaseJobsRepo


class UpdateJobService(UpdateJobUseCase):
    """Applies a partial update to an existing Job definition."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: UpdateJobInput) -> UpdateJobOutput:
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        if request.enabled is not None:
            job.enabled = request.enabled
        if request.catalog is not None:
            job.catalog = request.catalog
        if request.cron is not None:
            job.cron = request.cron
        if request.job_config is not None:
            job.job_config = request.job_config
        job.updated_at = datetime.now(UTC)

        job = self._repo.update(job)

        return UpdateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            enabled=job.enabled,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
