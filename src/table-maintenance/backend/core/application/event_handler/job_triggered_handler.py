"""Define the handler for JobTriggered events."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import JobRun, JobRunId
from core.base.event_handler import EventHandler

if TYPE_CHECKING:
    from core.application.domain.model.job.events import JobTriggered
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class JobTriggeredHandler(EventHandler["JobTriggered"]):
    """Handle JobTriggered by creating a new PENDING JobRun.

    After handling, the created run is available via ``last_created_run``.
    This allows synchronous callers (e.g. CreateJobRunService) to
    retrieve the result after dispatching events.
    """

    def __init__(self, job_runs_repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._job_runs_repo = job_runs_repo
        self.last_created_run: JobRun | None = None

    def handle(self, event: JobTriggered) -> None:
        """Create and persist a new JobRun for the triggered job."""
        run = JobRun.create(
            id=JobRunId(value=f"{event.job_id.value}-{secrets.token_hex(3)}"),
            job_id=event.job_id,
            trigger_type=event.trigger_type,
            started_at=datetime.now(UTC),
        )
        self._job_runs_repo.create(run)
        self.last_created_run = run
