from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job import Job, JobId, JobType
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job.jobs_repo import JobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Creates a Job definition only. Triggering a run is a separate use case."""

    def __init__(self, repo: JobsRepo) -> None:
        self._repo = repo

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        job_config = getattr(request, _CONFIG_BY_TYPE[request.job_type], None) or {}
        table = job_config.get("table", "")
        now = datetime.now(UTC)

        job = Job(
            id=JobId(value=secrets.token_hex(5)),
            job_type=JobType(request.job_type),
            created_at=now,
            updated_at=now,
            catalog=request.catalog,
            table=table,
            job_config=job_config,
            cron=request.cron,
            enabled=request.enabled,
        )
        job = self._repo.create(job)
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            enabled=job.enabled,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
