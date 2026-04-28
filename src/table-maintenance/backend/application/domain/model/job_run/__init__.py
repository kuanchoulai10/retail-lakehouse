"""JobRun aggregate root and related types."""

from __future__ import annotations

from application.domain.model.job_run.exceptions import (
    InvalidStateTransitionError,
    JobRunNotFoundError,
)
from application.domain.model.job_run.job_run import JobRun
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_result import JobRunResult
from application.domain.model.job_run.job_run_status import JobRunStatus
from application.domain.model.job_run.trigger_type import TriggerType

__all__ = [
    "InvalidStateTransitionError",
    "JobRun",
    "JobRunId",
    "JobRunNotFoundError",
    "JobRunResult",
    "JobRunStatus",
    "TriggerType",
]
