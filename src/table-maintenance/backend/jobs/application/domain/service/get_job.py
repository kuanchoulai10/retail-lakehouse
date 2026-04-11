from __future__ import annotations

from typing import TYPE_CHECKING

from jobs.application.domain.exceptions import JobNotFoundError
from jobs.application.exceptions import JobNotFoundError as AppJobNotFoundError
from jobs.application.port.inbound import GetJobInput, GetJobOutput, GetJobUseCase

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


class GetJobService(GetJobUseCase):
    """Implements GetJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: GetJobInput) -> GetJobOutput:
        try:
            job = self._repo.get(request.job_id)
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e
        return GetJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
        )
