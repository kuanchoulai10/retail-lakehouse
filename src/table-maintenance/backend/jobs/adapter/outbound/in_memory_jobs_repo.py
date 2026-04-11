from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from jobs.adapter.outbound.k8s.status_mapper import status_from_k8s
from jobs.application.domain.exceptions import JobNotFoundError
from jobs.application.domain.job import Job
from jobs.application.domain.job_id import JobId
from jobs.application.domain.job_type import JobType
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

if TYPE_CHECKING:
    from jobs.adapter.inbound.web.dto import JobApiRequest as JobRequest


class InMemoryJobsRepo(BaseJobsRepo):
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, request: JobRequest) -> Job:
        job_id = JobId(value=secrets.token_hex(5))
        kind = "ScheduledSparkApplication" if request.cron else "SparkApplication"
        job = Job(
            id=job_id,
            job_type=JobType(request.job_type),
            status=status_from_k8s(kind, ""),
            created_at=datetime.now(UTC),
        )
        self._jobs[job_id.value] = job
        return job

    def list_all(self) -> list[Job]:
        return list(self._jobs.values())

    def get(self, name: str) -> Job:
        try:
            return self._jobs[name]
        except KeyError:
            raise JobNotFoundError(name) from None

    def delete(self, name: str) -> None:
        try:
            del self._jobs[name]
        except KeyError:
            raise JobNotFoundError(name) from None
