from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from jobs.application.domain.model.job import Job
from jobs.application.domain.model.job_id import JobId
from jobs.application.domain.model.job_status import JobStatus
from jobs.application.domain.model.job_type import JobType
from jobs.application.port.inbound import CreateJobInput, CreateJobOutput, CreateJobUseCase

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Implements CreateJobUseCase by delegating to the jobs repository."""

    def __init__(self, repo: BaseJobsRepo) -> None:
        self._repo = repo

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        job_config = getattr(request, _CONFIG_BY_TYPE[request.job_type], None) or {}
        table = job_config.get("table", "")

        job = Job(
            id=JobId(value=secrets.token_hex(5)),
            job_type=JobType(request.job_type),
            status=JobStatus.PENDING,
            created_at=datetime.now(UTC),
            catalog=request.catalog,
            table=table,
            job_config=job_config,
            cron=request.cron,
        )
        job = self._repo.create(job)
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
        )
