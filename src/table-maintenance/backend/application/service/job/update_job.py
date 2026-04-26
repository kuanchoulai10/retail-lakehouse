"""Define the UpdateJobService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job import (
    CronExpression,
    JobId,
    JobNotFoundError,
    JobStatus,
    TableReference,
)
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    UpdateJobInput,
    UpdateJobOutput,
    UpdateJobUseCase,
)

if TYPE_CHECKING:
    from application.service.outbox.event_serializer import EventSerializer
    from application.port.outbound.event_outbox.event_outbox_store import (
        EventOutboxStore,
    )
    from application.port.outbound.job.jobs_repo import JobsRepo

_STATUS_ACTION = {
    JobStatus.ACTIVE: "resume",
    JobStatus.PAUSED: "pause",
    JobStatus.ARCHIVED: "archive",
}


class UpdateJobService(UpdateJobUseCase):
    """Applies a partial update to an existing Job definition."""

    def __init__(
        self, repo: JobsRepo, outbox_repo: EventOutboxStore, serializer: EventSerializer
    ) -> None:
        """Initialize with the jobs repository, outbox repo, and serializer."""
        self._repo = repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self, request: UpdateJobInput) -> UpdateJobOutput:
        """Apply partial updates to the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        if request.status is not None:
            target = JobStatus(request.status)
            action = _STATUS_ACTION[target]
            getattr(job, action)()

        job.apply_changes(
            table_ref=TableReference(catalog=request.catalog, table=job.table_ref.table)
            if request.catalog is not None
            else None,
            cron=CronExpression(expression=request.cron)
            if request.cron is not None
            else None,
            job_config=request.job_config,
        )
        job.updated_at = datetime.now(UTC)

        job = self._repo.update(job)
        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)

        return UpdateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
