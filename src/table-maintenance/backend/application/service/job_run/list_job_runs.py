"""Define the ListJobRunsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobId
from application.port.inbound import (
    ListJobRunsUseCaseInput,
    ListJobRunsUseCaseOutput,
    ListJobRunsUseCaseOutputItem,
    ListJobRunsUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class ListJobRunsService(ListJobRunsUseCase):
    """Lists all runs for a given Job."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: ListJobRunsUseCaseInput) -> ListJobRunsUseCaseOutput:
        """Return all job runs for the specified job."""
        runs = self._repo.list_for_job(JobId(value=request.job_id))
        return ListJobRunsUseCaseOutput(
            runs=[
                ListJobRunsUseCaseOutputItem(
                    run_id=r.id.value,
                    job_id=r.job_id.value,
                    status=r.status.value,
                    trigger_type=r.trigger_type.value,
                    started_at=r.started_at,
                    finished_at=r.finished_at,
                )
                for r in runs
            ],
        )
