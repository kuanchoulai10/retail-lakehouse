from __future__ import annotations

from typing import TYPE_CHECKING

from jobs.application.domain.model.exceptions import JobNotFoundError
from jobs.application.exceptions import JobNotFoundError as AppJobNotFoundError
from jobs.application.port.inbound import DeleteJobInput, DeleteJobOutput, DeleteJobUseCase

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


class DeleteJobService(DeleteJobUseCase):
    """Implements DeleteJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: DeleteJobInput) -> DeleteJobOutput:
        try:
            self._repo.delete(request.job_id)
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e
        return DeleteJobOutput()
