"""Define the JobRun aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.aggregate_root import AggregateRoot

from application.domain.model.job_run.exceptions import InvalidStateTransitionError
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_status import JobRunStatus
from application.domain.model.job_run.trigger_type import TriggerType

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.job_id import JobId


@dataclass(eq=False)
class JobRun(AggregateRoot[JobRunId]):
    """A single execution of a Job — the aggregate root for run history."""

    id: JobRunId
    job_id: JobId
    status: JobRunStatus
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def _transition_to(self, target: JobRunStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidStateTransitionError(self.status.value, target.value)
        self.status = target

    def mark_running(self, started_at: datetime) -> None:
        """Transition from PENDING to RUNNING."""
        self._transition_to(JobRunStatus.RUNNING)
        self.started_at = started_at

    def mark_completed(self, finished_at: datetime) -> None:
        """Transition from RUNNING to COMPLETED."""
        self._transition_to(JobRunStatus.COMPLETED)
        self.finished_at = finished_at

    def mark_failed(self, finished_at: datetime) -> None:
        """Transition from PENDING or RUNNING to FAILED."""
        self._transition_to(JobRunStatus.FAILED)
        self.finished_at = finished_at

    def cancel(self) -> None:
        """Transition from PENDING or RUNNING to CANCELLED."""
        self._transition_to(JobRunStatus.CANCELLED)
