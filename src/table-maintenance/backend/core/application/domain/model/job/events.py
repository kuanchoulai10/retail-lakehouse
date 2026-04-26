"""Define domain events for the Job aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.domain_event import DomainEvent

if TYPE_CHECKING:
    from core.application.domain.model.job.cron_expression import CronExpression
    from core.application.domain.model.job.field_change import FieldChange
    from core.application.domain.model.job.job_id import JobId
    from core.application.domain.model.job.job_type import JobType
    from core.application.domain.model.job.table_reference import TableReference
    from core.application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobCreated(DomainEvent):
    """Raised when a new Job is created via the factory method."""

    job_id: JobId
    job_type: JobType
    table_ref: TableReference
    cron: CronExpression | None


@dataclass(frozen=True)
class JobUpdated(DomainEvent):
    """Raised when Job configuration fields are changed."""

    job_id: JobId
    changes: tuple[FieldChange, ...]


@dataclass(frozen=True)
class JobPaused(DomainEvent):
    """Raised when a Job transitions from ACTIVE to PAUSED."""

    job_id: JobId


@dataclass(frozen=True)
class JobResumed(DomainEvent):
    """Raised when a Job transitions from PAUSED to ACTIVE."""

    job_id: JobId


@dataclass(frozen=True)
class JobArchived(DomainEvent):
    """Raised when a Job transitions to ARCHIVED (end-of-life)."""

    job_id: JobId


@dataclass(frozen=True)
class JobTriggered(DomainEvent):
    """Raised when a Job is triggered to create a new run."""

    job_id: JobId
    trigger_type: TriggerType
