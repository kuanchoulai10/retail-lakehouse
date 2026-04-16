from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job import Job
from application.domain.model.job_id import JobId
from application.domain.model.job_status import JobStatus
from application.domain.model.job_type import JobType
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run_executor import JobRunExecutor
    from application.port.outbound.jobs_repo import BaseJobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Creates a Job definition, then triggers a run if enabled.

    During the Job/JobRun split transition, `enabled` is hardcoded to True so
    POST /jobs preserves its pre-split side-effect of triggering K8s. Stage 7
    will take `enabled` from the request and default it to False.
    """

    def __init__(self, repo: BaseJobsRepo, executor: JobRunExecutor) -> None:
        self._repo = repo
        self._executor = executor

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        job_config = getattr(request, _CONFIG_BY_TYPE[request.job_type], None) or {}
        table = job_config.get("table", "")
        now = datetime.now(UTC)

        job = Job(
            id=JobId(value=secrets.token_hex(5)),
            job_type=JobType(request.job_type),
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            catalog=request.catalog,
            table=table,
            job_config=job_config,
            cron=request.cron,
            enabled=True,
        )
        job = self._repo.create(job)
        if job.enabled:
            self._executor.trigger(job)
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
        )
