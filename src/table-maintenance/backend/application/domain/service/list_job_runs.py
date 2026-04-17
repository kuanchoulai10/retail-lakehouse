from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobId
from application.port.inbound import (
    ListJobRunsInput,
    ListJobRunsOutput,
    ListJobRunsOutputItem,
    ListJobRunsUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_runs_repo import BaseJobRunsRepo


class ListJobRunsService(ListJobRunsUseCase):
    """Lists all runs for a given Job."""

    def __init__(self, repo: BaseJobRunsRepo) -> None:
        self._repo = repo

    def execute(self, request: ListJobRunsInput) -> ListJobRunsOutput:
        runs = self._repo.list_for_job(JobId(value=request.job_id))
        return ListJobRunsOutput(
            runs=[
                ListJobRunsOutputItem(
                    run_id=r.id.value,
                    job_id=r.job_id.value,
                    status=r.status.value,
                    started_at=r.started_at,
                    finished_at=r.finished_at,
                )
                for r in runs
            ],
        )
