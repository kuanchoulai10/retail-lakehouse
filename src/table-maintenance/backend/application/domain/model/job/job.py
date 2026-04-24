"""Define the Job aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from application.domain.model.job.exceptions import (
    InvalidJobStateTransitionError,
    JobNotActiveError,
    MaxActiveRunsExceededError,
)
from application.domain.model.job.job_id import JobId
from application.domain.model.job.job_status import JobStatus
from application.domain.model.job_run.job_run import JobRun
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_status import JobRunStatus

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.job_type import JobType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context.

    Execution state lives in the JobRun aggregate, not on the Job.
    """

    id: JobId
    job_type: JobType
    created_at: datetime
    updated_at: datetime
    catalog: str = ""
    table: str = ""
    job_config: dict | None = None
    cron: str | None = None
    status: JobStatus = JobStatus.ACTIVE
    next_run_at: datetime | None = None
    max_active_runs: int = 1

    def __post_init__(self) -> None:
        """Initialize job_config to an empty dict if not provided."""
        if self.job_config is None:
            self.job_config = {}

    @property
    def is_active(self) -> bool:
        """Return True if the job is in ACTIVE status."""
        return self.status == JobStatus.ACTIVE

    def _transition_to(self, target: JobStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidJobStateTransitionError(self.status.value, target.value)
        self.status = target

    def pause(self) -> None:
        """Transition from ACTIVE to PAUSED."""
        self._transition_to(JobStatus.PAUSED)

    def resume(self) -> None:
        """Transition from PAUSED to ACTIVE."""
        self._transition_to(JobStatus.ACTIVE)

    def archive(self) -> None:
        """Transition from ACTIVE or PAUSED to ARCHIVED."""
        self._transition_to(JobStatus.ARCHIVED)

    def trigger(
        self,
        run_id: JobRunId,
        now: datetime,
        active_run_count: int,
    ) -> JobRun:
        """Create a new PENDING JobRun if the job is triggerable.

        Raises:
            JobNotActiveError: if the job is not ACTIVE.
            MaxActiveRunsExceededError: if active_run_count >= max_active_runs.
        """
        if not self.is_active:
            raise JobNotActiveError(self.id.value)
        if active_run_count >= self.max_active_runs:
            raise MaxActiveRunsExceededError(self.id.value, self.max_active_runs)
        return JobRun(
            id=run_id,
            job_id=self.id,
            status=JobRunStatus.PENDING,
            started_at=now,
        )
