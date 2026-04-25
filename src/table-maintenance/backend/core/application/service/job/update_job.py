"""Define the UpdateJobService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job import (
    CronExpression,
    JobId,
    JobNotFoundError,
    JobStatus,
    TableReference,
)
from core.application.exceptions import JobNotFoundError as AppJobNotFoundError
from core.application.port.inbound import (
    UpdateJobInput,
    UpdateJobOutput,
    UpdateJobUseCase,
)

if TYPE_CHECKING:
    from core.application.event_handler.event_dispatcher import EventDispatcher
    from core.application.port.outbound.job.jobs_repo import JobsRepo

_STATUS_ACTION = {
    JobStatus.ACTIVE: "resume",
    JobStatus.PAUSED: "pause",
    JobStatus.ARCHIVED: "archive",
}


class UpdateJobService(UpdateJobUseCase):
    """Applies a partial update to an existing Job definition."""

    def __init__(self, repo: JobsRepo, dispatcher: EventDispatcher) -> None:
        """Initialize with the jobs repository and event dispatcher."""
        self._repo = repo
        self._dispatcher = dispatcher

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
        self._dispatcher.dispatch_all(job.collect_events())

        return UpdateJobOutput(
            id=job.id.value,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
