"""Define domain events for the JobRun aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.domain_event import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from core.application.domain.model.job.job_id import JobId
    from core.application.domain.model.job_run.job_run_id import JobRunId
    from core.application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobRunCreated(DomainEvent):
    """Raised when a new JobRun is created via the factory method."""

    run_id: JobRunId
    job_id: JobId
    trigger_type: TriggerType


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
