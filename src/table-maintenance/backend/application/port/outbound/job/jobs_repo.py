"""Define the JobsRepo port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.repository import Repository

from application.domain.model.job import Job

if TYPE_CHECKING:
    from datetime import datetime

    from base.entity_id import EntityId

    from application.domain.model.job import JobId


class JobsRepo(Repository[Job]):
    """Repository for Job definitions.

    Extends the base Repository with mutation operations (``update``,
    ``delete``) — Jobs are mutable entities that can be edited in place
    (enable/disable, change schedule/config) and removed when no longer
    wanted. Also adds scheduling-specific queries.
    """

    @abstractmethod
    def update(self, entity: Job) -> Job:
        """Persist changes to an existing job and return the updated entity."""
        ...

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Remove a job by its identifier."""
        ...

    @abstractmethod
    def list_schedulable(self, now: datetime) -> list[Job]:
        """Return enabled jobs with a cron schedule whose next_run_at <= now."""
        ...

    @abstractmethod
    def save_next_run_at(self, job_id: JobId, next_run_at: datetime) -> None:
        """Persist the advanced next_run_at for a job."""
        ...
