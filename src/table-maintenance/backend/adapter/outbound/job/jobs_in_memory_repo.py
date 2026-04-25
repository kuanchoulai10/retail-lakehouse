"""Define the JobsInMemoryRepo adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobNotFoundError
from application.port.outbound.job.jobs_repo import JobsRepo

if TYPE_CHECKING:
    from datetime import datetime

    from core.base.entity_id import EntityId

    from application.domain.model.job import Job, JobId


class JobsInMemoryRepo(JobsRepo):
    """In-memory implementation of JobsRepo for testing."""

    def __init__(self) -> None:
        """Initialize an empty in-memory job store."""
        self._jobs: dict[str, Job] = {}

    def create(self, entity: Job) -> Job:
        """Store a new job in memory and return it."""
        self._jobs[entity.id.value] = entity
        return entity

    def list_all(self) -> list[Job]:
        """Return all stored jobs."""
        return list(self._jobs.values())

    def get(self, entity_id: EntityId) -> Job:
        """Return the job with the given id or raise JobNotFoundError."""
        try:
            return self._jobs[entity_id.value]
        except KeyError:
            raise JobNotFoundError(entity_id.value) from None

    def delete(self, entity_id: EntityId) -> None:
        """Remove the job with the given id or raise JobNotFoundError."""
        try:
            del self._jobs[entity_id.value]
        except KeyError:
            raise JobNotFoundError(entity_id.value) from None

    def update(self, entity: Job) -> Job:
        """Replace the stored job with the given entity or raise JobNotFoundError."""
        if entity.id.value not in self._jobs:
            raise JobNotFoundError(entity.id.value)
        self._jobs[entity.id.value] = entity
        return entity

    def list_schedulable(self, now: datetime) -> list[Job]:
        """Return enabled jobs with a cron schedule whose next_run_at <= now."""
        return [
            j
            for j in self._jobs.values()
            if j.is_active
            and j.cron is not None
            and j.next_run_at is not None
            and j.next_run_at <= now
        ]

    def save_next_run_at(self, job_id: JobId, next_run_at: datetime) -> None:
        """Update the next_run_at field of the given job."""
        if job_id.value not in self._jobs:
            raise JobNotFoundError(job_id.value)
        self._jobs[job_id.value].next_run_at = next_run_at
