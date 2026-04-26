"""Define domain events for the JobRun aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.domain_event import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.cron_expression import CronExpression
    from application.domain.model.job.job_id import JobId
    from application.domain.model.job.job_type import JobType
    from application.domain.model.job.resource_config import ResourceConfig
    from application.domain.model.job.table_reference import TableReference
    from application.domain.model.job_run.job_run_id import JobRunId
    from application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobRunCreated(DomainEvent):
    """Raised when a new JobRun is created via the factory method.

    Carries full Job context so downstream handlers (e.g. K8s executor)
    can act without querying the repository.
    """

    run_id: JobRunId
    job_id: JobId
    trigger_type: TriggerType
    job_type: JobType
    table_ref: TableReference
    job_config: dict
    resource_config: ResourceConfig
    cron: CronExpression | None


@dataclass(frozen=True)
class JobRunStarted(DomainEvent):
    """Raised when a JobRun transitions from PENDING to RUNNING."""

    run_id: JobRunId
    job_id: JobId
    started_at: datetime


@dataclass(frozen=True)
class JobRunCompleted(DomainEvent):
    """Raised when a JobRun transitions from RUNNING to COMPLETED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime


@dataclass(frozen=True)
class JobRunFailed(DomainEvent):
    """Raised when a JobRun transitions to FAILED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime


@dataclass(frozen=True)
class JobRunCancelled(DomainEvent):
    """Raised when a JobRun is cancelled."""

    run_id: JobRunId
    job_id: JobId
