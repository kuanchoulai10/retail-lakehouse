"""Define the OperationAttempt value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run.failure_class import (
    FailureClass,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.next_step import (
    NextStep,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.run_status import (
    RunStatus,
)

_ATTEMPT_STATUSES = frozenset({RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.SUCCEEDED, RunStatus.FAILED})


class OperationAttempt(ValueObject):
    """Record one attempt of a run's maintenance operation: its job, size, how it ended and what followed.

    ``started_at`` is when the attempt was submitted; ``started_running_at`` is when its driver started
    running, None while the attempt waits in its queue. ``job_name`` names the attempt's own Spark job,
    None until it is known. ``size`` is None for an attempt started without one. ``event_log_finished`` is
    None when the attempt's event log could not be read.
    """

    attempt: int
    size: ComputeSize | None
    status: RunStatus
    started_at: datetime
    job_name: str | None = None
    started_running_at: datetime | None = None
    finished_at: datetime | None = None
    failure_class: FailureClass | None = None
    error: str | None = None
    event_log_finished: bool | None = None
    next_step: NextStep | None = None
    next_size: ComputeSize | None = None

    @model_validator(mode="after")
    def _is_queued_running_or_done(self) -> OperationAttempt:
        if self.status not in _ATTEMPT_STATUSES:
            msg = f"attempt {self.attempt} is {self.status}: an attempt is queued, running, succeeded or failed"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _runs_no_earlier_than_it_was_submitted(self) -> OperationAttempt:
        if self.started_running_at is not None and self.started_running_at < self.started_at:
            msg = f"attempt {self.attempt} started running at {self.started_running_at}, before it was submitted"
            raise ValueError(msg)
        return self

    @property
    def finished(self) -> bool:
        """Return whether the attempt has an outcome."""
        return self.status not in (RunStatus.QUEUED, RunStatus.RUNNING)
