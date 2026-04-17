from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound import (
    ListJobsInput,
    ListJobsOutput,
    ListJobsOutputItem,
    ListJobsUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job.jobs_repo import BaseJobsRepo


class ListJobsService(ListJobsUseCase):
    """Implements ListJobsUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: ListJobsInput) -> ListJobsOutput:
        jobs = self._repo.list_all()
        return ListJobsOutput(
            jobs=[
                ListJobsOutputItem(
                    id=job.id.value,
                    job_type=job.job_type.value,
                    enabled=job.enabled,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
                for job in jobs
            ],
        )
