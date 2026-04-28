"""Define the GetJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobId, JobNotFoundError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    GetJobUseCaseInput,
    GetJobUseCaseOutput,
    GetJobUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job.jobs_repo import JobsRepo


class GetJobService(GetJobUseCase):
    """Implements GetJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: JobsRepo) -> None:
        """Initialize with the jobs repository."""
        self._repo = repo

    def execute(self, request: GetJobUseCaseInput) -> GetJobUseCaseOutput:
        """Retrieve a job by its identifier."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e
        return GetJobUseCaseOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
