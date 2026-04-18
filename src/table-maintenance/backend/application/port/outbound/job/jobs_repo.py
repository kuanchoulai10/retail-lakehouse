from __future__ import annotations

from abc import abstractmethod

from base.repository import Repository

from application.domain.model.job import Job


class JobsRepo(Repository[Job]):
    """Repository for Job definitions.

    Extends the generic CRUD Repository with an `update` operation so Jobs
    can be edited (enable/disable, change schedule/config) in place.
    """

    @abstractmethod
    def update(self, entity: Job) -> Job: ...
