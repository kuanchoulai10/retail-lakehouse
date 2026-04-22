"""Define the JobRunsInMemoryRepo adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunNotFoundError
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

if TYPE_CHECKING:
    from application.domain.model.job import JobId
    from application.domain.model.job_run import JobRun, JobRunId


class JobRunsInMemoryRepo(JobRunsRepo):
    """In-memory implementation of JobRunsRepo for testing."""

    def __init__(self) -> None:
        """Initialize an empty in-memory job-run store."""
        self._runs: dict[str, JobRun] = {}

    def create(self, entity: JobRun) -> JobRun:
        """Store a new job run in memory and return it."""
        self._runs[entity.id.value] = entity
        return entity

    def get(self, run_id: JobRunId) -> JobRun:
        """Return the job run with the given id or raise JobRunNotFoundError."""
        try:
            return self._runs[run_id.value]
        except KeyError:
            raise JobRunNotFoundError(run_id.value) from None

    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        """Return all job runs belonging to the given job."""
        return [r for r in self._runs.values() if r.job_id == job_id]

    def list_all(self) -> list[JobRun]:
        """Return all stored job runs."""
        return list(self._runs.values())

    def count_active_for_job(self, job_id: JobId) -> int:
        """Return the count of non-terminal runs (pending or running) for a job."""
        return sum(
            1
            for r in self._runs.values()
            if r.job_id == job_id and r.status in ("pending", "running")
        )
