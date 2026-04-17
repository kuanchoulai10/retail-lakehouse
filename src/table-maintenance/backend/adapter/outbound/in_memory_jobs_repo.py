from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import JobNotFoundError
from application.port.outbound.job.jobs_repo import BaseJobsRepo

if TYPE_CHECKING:
    from base.entity_id import EntityId

    from application.domain.model.job import Job


class InMemoryJobsRepo(BaseJobsRepo):
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, entity: Job) -> Job:
        self._jobs[entity.id.value] = entity
        return entity

    def list_all(self) -> list[Job]:
        return list(self._jobs.values())

    def get(self, entity_id: EntityId) -> Job:
        try:
            return self._jobs[entity_id.value]
        except KeyError:
            raise JobNotFoundError(entity_id.value) from None

    def delete(self, entity_id: EntityId) -> None:
        try:
            del self._jobs[entity_id.value]
        except KeyError:
            raise JobNotFoundError(entity_id.value) from None

    def update(self, entity: Job) -> Job:
        if entity.id.value not in self._jobs:
            raise JobNotFoundError(entity.id.value)
        self._jobs[entity.id.value] = entity
        return entity
