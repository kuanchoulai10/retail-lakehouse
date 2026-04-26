"""Define the CreateJobService."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    TableReference,
)
from application.port.inbound import (
    CreateJobInput,
    CreateJobOutput,
    CreateJobUseCase,
)

if TYPE_CHECKING:
    from application.service.outbox.event_serializer import EventSerializer
    from application.port.outbound.event_outbox_repo import EventOutboxRepo
    from application.port.outbound.job.jobs_repo import JobsRepo

_CONFIG_BY_TYPE = {
    "expire_snapshots": "expire_snapshots",
    "remove_orphan_files": "remove_orphan_files",
    "rewrite_data_files": "rewrite_data_files",
    "rewrite_manifests": "rewrite_manifests",
}


class CreateJobService(CreateJobUseCase):
    """Creates a Job definition only. Triggering a run is a separate use case."""

    def __init__(
        self, repo: JobsRepo, outbox_repo: EventOutboxRepo, serializer: EventSerializer
    ) -> None:
        """Initialize with the jobs repository, outbox repo, and serializer."""
        self._repo = repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self, request: CreateJobInput) -> CreateJobOutput:
        """Create a new job from the given input and persist it."""
        job_config = getattr(request, _CONFIG_BY_TYPE[request.job_type], None) or {}
        table = job_config.get("table", "")
        now = datetime.now(UTC)

        job = Job.create(
            id=JobId(value=secrets.token_hex(5)),
            job_type=JobType(request.job_type),
            created_at=now,
            updated_at=now,
            table_ref=TableReference(catalog=request.catalog, table=table),
            job_config=job_config,
            cron=CronExpression(expression=request.cron) if request.cron else None,
            status=JobStatus(request.status),
        )
        job = self._repo.create(job)
        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)
        return CreateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
