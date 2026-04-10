from __future__ import annotations

from typing import TYPE_CHECKING

from jobs.application.port.inbound.get_job import GetJobUseCase

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
    from jobs.domain.job import Job


class GetJobService(GetJobUseCase):
    """Implements GetJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: str) -> Job:
        return self._repo.get(request)
