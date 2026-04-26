"""Define the handler for JobTriggered events."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import JobRun, JobRunId
from base.event_handler import EventHandler

if TYPE_CHECKING:
    from core.application.domain.model.job.events import JobTriggered
    from core.application.service.outbox.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class JobTriggeredHandler(EventHandler["JobTriggered"]):
    """Handle JobTriggered by creating a new PENDING JobRun.

    Writes the JobRun's own events (JobRunCreated) to the outbox
    for downstream consumers.
    """

    def __init__(
        self,
        job_runs_repo: JobRunsRepo,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with job runs repo, outbox repo, and serializer."""
        self._job_runs_repo = job_runs_repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def handle(self, event: JobTriggered) -> None:
        """Create and persist a new JobRun, write its events to outbox."""
        run = JobRun.create(
            id=JobRunId(value=f"{event.job_id.value}-{secrets.token_hex(3)}"),
            job_id=event.job_id,
            trigger_type=event.trigger_type,
            started_at=datetime.now(UTC),
        )
        self._job_runs_repo.create(run)
        entries = self._serializer.to_outbox_entries(
            events=run.collect_events(),
            aggregate_type="JobRun",
            aggregate_id=run.id.value,
        )
        self._outbox_repo.save(entries)
