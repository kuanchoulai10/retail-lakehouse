from __future__ import annotations

from base.repository import Repository

from jobs.application.domain.model.job import Job


class BaseJobsRepo(Repository[Job]):
    pass
