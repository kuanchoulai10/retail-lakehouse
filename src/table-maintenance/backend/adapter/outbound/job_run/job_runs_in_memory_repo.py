from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunNotFoundError
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

if TYPE_CHECKING:
    from application.domain.model.job import JobId
    from application.domain.model.job_run import JobRun, JobRunId


class JobRunsInMemoryRepo(JobRunsRepo):
    def __init__(self) -> None:
        self._runs: dict[str, JobRun] = {}

    def create(self, entity: JobRun) -> JobRun:
        self._runs[entity.id.value] = entity
        return entity

    def get(self, run_id: JobRunId) -> JobRun:
        try:
            return self._runs[run_id.value]
        except KeyError:
            raise JobRunNotFoundError(run_id.value) from None

    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        return [r for r in self._runs.values() if r.job_id == job_id]

    def list_all(self) -> list[JobRun]:
        return list(self._runs.values())
