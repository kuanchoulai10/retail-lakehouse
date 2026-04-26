"""Define the DeleteJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobId, JobNotFoundError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    DeleteJobInput,
    DeleteJobOutput,
    DeleteJobUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job.jobs_repo import JobsRepo


class DeleteJobService(DeleteJobUseCase):
    """Implements DeleteJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: JobsRepo) -> None:
        """Initialize with the jobs repository."""
        self._repo = repo

    def execute(self, request: DeleteJobInput) -> DeleteJobOutput:
        """Delete the job identified by the input."""
        try:
            self._repo.delete(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e
        return DeleteJobOutput()
