"""Define the JobRunsRepo port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.repository import Repository

from application.domain.model.job_run import JobRun

if TYPE_CHECKING:
    from application.domain.model.job import JobId


class JobRunsRepo(Repository[JobRun]):
    """Repository for JobRun execution instances.

    JobRuns are append-only historical records — once created they are
    updated through their lifecycle (running → completed/failed/cancelled)
    but never deleted, so this port does not expose ``delete``. Adds
    ``save`` for state transitions and aggregate-specific queries.
    """

    @abstractmethod
    def save(self, entity: JobRun) -> JobRun:
        """Persist changes to an existing job run and return it."""
        ...

    @abstractmethod
    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        """Return all job runs for the given job."""
        ...

    @abstractmethod
    def count_active_for_job(self, job_id: JobId) -> int:
        """Return the count of non-terminal runs (pending or running) for a job."""
        ...
