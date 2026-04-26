"""Define the Job aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from core.application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from core.application.domain.model.job.field_change import FieldChange
from core.application.domain.model.job.exceptions import (
    InvalidJobStateTransitionError,
    JobNotActiveError,
    MaxActiveRunsExceededError,
)
from core.application.domain.model.job.cron_expression import CronExpression
from core.application.domain.model.job.job_id import JobId
from core.application.domain.model.job.job_status import JobStatus
from core.application.domain.model.job.table_reference import TableReference
from core.application.domain.model.job_run.trigger_type import TriggerType

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job.job_type import JobType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context.

    Execution state lives in the JobRun aggregate, not on the Job.
    """

    id: JobId
    job_type: JobType
    created_at: datetime
    updated_at: datetime
    table_ref: TableReference = TableReference(catalog="", table="")
    job_config: dict | None = None
    cron: CronExpression | None = None
    status: JobStatus = JobStatus.ACTIVE
    next_run_at: datetime | None = None
    max_active_runs: int = 1

    def __post_init__(self) -> None:
        """Initialize job_config to an empty dict if not provided."""
        if self.job_config is None:
            self.job_config = {}

    @classmethod
    def create(
        cls,
        id: JobId,
        job_type: JobType,
        created_at: datetime,
        updated_at: datetime,
        table_ref: TableReference = TableReference(catalog="", table=""),
        job_config: dict | None = None,
        cron: CronExpression | None = None,
        status: JobStatus = JobStatus.ACTIVE,
        next_run_at: datetime | None = None,
        max_active_runs: int = 1,
    ) -> Job:
        """Create a new Job and register a JobCreated event."""
        job = cls(
            id=id,
            job_type=job_type,
            created_at=created_at,
            updated_at=updated_at,
            table_ref=table_ref,
            job_config=job_config,
            cron=cron,
            status=status,
            next_run_at=next_run_at,
            max_active_runs=max_active_runs,
        )
        job.register_event(
            JobCreated(
                job_id=id,
                job_type=job_type,
                table_ref=table_ref,
                cron=cron,
            )
        )
        return job

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
        self.register_event(JobPaused(job_id=self.id))

    def resume(self) -> None:
        """Transition from PAUSED to ACTIVE."""
        self._transition_to(JobStatus.ACTIVE)
        self.register_event(JobResumed(job_id=self.id))

    def archive(self) -> None:
        """Transition from ACTIVE or PAUSED to ARCHIVED."""
        self._transition_to(JobStatus.ARCHIVED)
        self.register_event(JobArchived(job_id=self.id))

    def trigger(
        self,
        active_run_count: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> None:
        """Guard trigger invariants and register a JobTriggered event.

        Raises:
            JobNotActiveError: if the job is not ACTIVE.
            MaxActiveRunsExceededError: if active_run_count >= max_active_runs.
        """
        if not self.is_active:
            raise JobNotActiveError(self.id.value)
        if active_run_count >= self.max_active_runs:
            raise MaxActiveRunsExceededError(self.id.value, self.max_active_runs)
        self.register_event(JobTriggered(job_id=self.id, trigger_type=trigger_type))

    def apply_changes(
        self,
        table_ref: TableReference | None = None,
        cron: CronExpression | None = None,
        job_config: dict | None = None,
    ) -> None:
        """Apply configuration changes and register a JobUpdated event if anything changed."""
        changes: list[FieldChange] = []
        if table_ref is not None and table_ref != self.table_ref:
            changes.append(
                FieldChange(
                    field="table_ref",
                    old_value=str(self.table_ref),
                    new_value=str(table_ref),
                )
            )
            self.table_ref = table_ref
        if cron is not None and cron != self.cron:
            changes.append(
                FieldChange(field="cron", old_value=str(self.cron), new_value=str(cron))
            )
            self.cron = cron
        if job_config is not None and job_config != self.job_config:
            changes.append(
                FieldChange(
                    field="job_config",
                    old_value=str(self.job_config),
                    new_value=str(job_config),
                )
            )
            self.job_config = job_config
        if changes:
            self.register_event(JobUpdated(job_id=self.id, changes=tuple(changes)))
