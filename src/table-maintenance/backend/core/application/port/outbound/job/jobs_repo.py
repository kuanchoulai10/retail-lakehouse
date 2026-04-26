"""Define the JobsRepo port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.repository import Repository

from core.application.domain.model.job import Job

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job import JobId


class JobsRepo(Repository[Job]):
    """Repository for Job definitions.

    Extends the generic CRUD Repository with an `update` operation so Jobs
    can be edited (enable/disable, change schedule/config) in place.
    """

    @abstractmethod
    def update(self, entity: Job) -> Job:
        """Persist changes to an existing job and return the updated entity."""
        ...

    @abstractmethod
    def list_schedulable(self, now: datetime) -> list[Job]:
        """Return enabled jobs with a cron schedule whose next_run_at <= now."""
        ...

    @abstractmethod
    def save_next_run_at(self, job_id: JobId, next_run_at: datetime) -> None:
        """Persist the advanced next_run_at for a job."""
        ...
