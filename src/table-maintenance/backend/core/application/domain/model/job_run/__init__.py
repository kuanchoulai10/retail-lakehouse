"""JobRun aggregate root and related types."""

from __future__ import annotations

from core.application.domain.model.job_run.exceptions import (
    InvalidStateTransitionError,
    JobRunNotFoundError,
)
from core.application.domain.model.job_run.job_run import JobRun
from core.application.domain.model.job_run.job_run_id import JobRunId
from core.application.domain.model.job_run.job_run_status import JobRunStatus
from core.application.domain.model.job_run.trigger_type import TriggerType

__all__ = [
    "InvalidStateTransitionError",
    "JobRun",
    "JobRunId",
    "JobRunNotFoundError",
    "JobRunStatus",
    "TriggerType",
]
