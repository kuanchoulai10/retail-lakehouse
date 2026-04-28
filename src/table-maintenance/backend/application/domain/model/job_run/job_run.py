"""Define the JobRun aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)
from application.domain.model.job_run.exceptions import InvalidStateTransitionError
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_status import JobRunStatus
from application.domain.model.job_run.trigger_type import TriggerType

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.cron_expression import CronExpression
    from application.domain.model.job.job_id import JobId
    from application.domain.model.job.job_type import JobType
    from application.domain.model.job.resource_config import ResourceConfig
    from application.domain.model.job.table_reference import TableReference
    from application.domain.model.job_run.job_run_result import JobRunResult


@dataclass(eq=False)
class JobRun(AggregateRoot[JobRunId]):
    """A single execution of a Job — the aggregate root for run history."""

    id: JobRunId
    job_id: JobId
    status: JobRunStatus
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: JobRunResult | None = None
    error: str | None = None

    @classmethod
    def create(
        cls,
        id: JobRunId,
        job_id: JobId,
        trigger_type: TriggerType,
        started_at: datetime,
        job_type: JobType,
        table_ref: TableReference,
        job_config: dict,
        resource_config: ResourceConfig,
        cron: CronExpression | None = None,
    ) -> JobRun:
        """Create a new PENDING JobRun and register a JobRunCreated event."""
        run = cls(
            id=id,
            job_id=job_id,
            status=JobRunStatus.PENDING,
            trigger_type=trigger_type,
            started_at=started_at,
        )
        run.register_event(
            JobRunCreated(
                run_id=id,
                job_id=job_id,
                trigger_type=trigger_type,
                job_type=job_type,
                table_ref=table_ref,
                job_config=job_config,
                resource_config=resource_config,
                cron=cron,
            )
        )
        return run

    def _transition_to(self, target: JobRunStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidStateTransitionError(self.status.value, target.value)
        self.status = target

    def mark_running(self, started_at: datetime) -> None:
        """Transition from PENDING to RUNNING."""
        self._transition_to(JobRunStatus.RUNNING)
        self.started_at = started_at
        self.register_event(
            JobRunStarted(run_id=self.id, job_id=self.job_id, started_at=started_at)
        )

    def mark_completed(self, finished_at: datetime, result: JobRunResult) -> None:
        """Transition from RUNNING to COMPLETED."""
        self._transition_to(JobRunStatus.COMPLETED)
        self.finished_at = finished_at
        self.result = result
        self.register_event(
            JobRunCompleted(
                run_id=self.id,
                job_id=self.job_id,
                finished_at=finished_at,
                result=result,
            )
        )

    def mark_failed(
        self,
        finished_at: datetime,
        error: str,
        result: JobRunResult | None = None,
    ) -> None:
        """Transition from PENDING or RUNNING to FAILED."""
        self._transition_to(JobRunStatus.FAILED)
        self.finished_at = finished_at
        self.error = error
        self.result = result
        self.register_event(
            JobRunFailed(
                run_id=self.id,
                job_id=self.job_id,
                finished_at=finished_at,
                error=error,
                result=result,
            )
        )

    def cancel(self) -> None:
        """Transition from PENDING or RUNNING to CANCELLED."""
        self._transition_to(JobRunStatus.CANCELLED)
        self.register_event(JobRunCancelled(run_id=self.id, job_id=self.job_id))
