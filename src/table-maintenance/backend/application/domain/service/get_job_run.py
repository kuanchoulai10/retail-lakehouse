from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.exceptions import JobRunNotFoundError
from application.domain.model.job_run_id import JobRunId
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound import GetJobRunInput, GetJobRunOutput, GetJobRunUseCase

if TYPE_CHECKING:
    from application.port.outbound.job_runs_repo import BaseJobRunsRepo


class GetJobRunService(GetJobRunUseCase):
    """Retrieves a single JobRun by id."""

    def __init__(self, repo: BaseJobRunsRepo) -> None:
        self._repo = repo

    def execute(self, request: GetJobRunInput) -> GetJobRunOutput:
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        return GetJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
