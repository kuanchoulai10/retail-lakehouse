from __future__ import annotations

from base.repository import Repository

from application.domain.model.job import Job


class BaseJobsRepo(Repository[Job]):
    pass
