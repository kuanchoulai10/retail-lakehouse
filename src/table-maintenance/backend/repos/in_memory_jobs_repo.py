from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from models.job_response import JobResponse
from models.job_status import status_from_k8s

if TYPE_CHECKING:
    from models.job_request import JobRequest

from repos.base_jobs_repo import BaseJobsRepo
from repos.exceptions import JobNotFoundError


class InMemoryJobsRepo(BaseJobsRepo):
    def __init__(self) -> None:
        self._jobs: dict[str, JobResponse] = {}

    def create(self, request: JobRequest) -> JobResponse:
        suffix = uuid.uuid4().hex[:8]
        name = f"table-maintenance-{request.job_type.value.replace('_', '-')}-{suffix}"
        kind = "ScheduledSparkApplication" if request.cron else "SparkApplication"
        response = JobResponse(
            name=name,
            kind=kind,
            namespace="default",
            job_type=request.job_type,
            status=status_from_k8s(kind, ""),
            created_at=datetime.now(UTC),
        )
        self._jobs[name] = response
        return response

    def list_all(self) -> list[JobResponse]:
        return list(self._jobs.values())

    def get(self, name: str) -> JobResponse:
        try:
            return self._jobs[name]
        except KeyError:
            raise JobNotFoundError(name) from None

    def delete(self, name: str) -> None:
        try:
            del self._jobs[name]
        except KeyError:
            raise JobNotFoundError(name) from None
