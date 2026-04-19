"""Define the JobRunsRepo port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.job import JobId
    from application.domain.model.job_run import JobRun, JobRunId


class JobRunsRepo(ABC):
    """Port over JobRun execution instances."""

    @abstractmethod
    def create(self, entity: JobRun) -> JobRun:
        """Persist a new job run and return it."""
        ...

    @abstractmethod
    def get(self, run_id: JobRunId) -> JobRun:
        """Retrieve a job run by its identifier."""
        ...

    @abstractmethod
    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        """Return all job runs for the given job."""
        ...

    @abstractmethod
    def list_all(self) -> list[JobRun]:
        """Return all job runs."""
        ...
