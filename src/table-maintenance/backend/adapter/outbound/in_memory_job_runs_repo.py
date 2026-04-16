from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.exceptions import JobRunNotFoundError
from application.port.outbound.job_runs_repo import BaseJobRunsRepo

if TYPE_CHECKING:
    from application.domain.model.job_id import JobId
    from application.domain.model.job_run import JobRun
    from application.domain.model.job_run_id import JobRunId


class InMemoryJobRunsRepo(BaseJobRunsRepo):
    def __init__(self) -> None:
        self._runs: dict[str, JobRun] = {}

    def add(self, run: JobRun) -> None:
        """Seed the repo with a run (test helper, not part of BaseJobRunsRepo)."""
        self._runs[run.id.value] = run

    def get(self, run_id: JobRunId) -> JobRun:
        try:
            return self._runs[run_id.value]
        except KeyError:
            raise JobRunNotFoundError(run_id.value) from None

    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        return [r for r in self._runs.values() if r.job_id == job_id]

    def list_all(self) -> list[JobRun]:
        return list(self._runs.values())
