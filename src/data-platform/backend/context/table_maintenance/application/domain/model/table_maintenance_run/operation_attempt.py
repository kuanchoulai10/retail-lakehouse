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
from context.table_maintenance.application.domain.model.table_maintenance_run.operation_run_status import (
    OperationRunStatus,
)


class OperationAttempt(ValueObject):
    """Record one attempt of a maintenance operation: its size, how it ended and what followed.

    ``started_at`` is when the attempt was submitted; ``started_running_at`` is when its driver started
    running, None while the attempt waits in its queue. ``size`` is None for an attempt started before
    sizes existed. ``event_log_finished`` is None when the attempt's event log could not be read.
    """

    attempt: int
    size: ComputeSize | None
    status: OperationRunStatus
    started_at: datetime
    started_running_at: datetime | None = None
    finished_at: datetime | None = None
    failure_class: FailureClass | None = None
    error: str | None = None
    event_log_finished: bool | None = None
    next_step: NextStep | None = None
    next_size: ComputeSize | None = None

    @model_validator(mode="after")
    def _runs_no_earlier_than_it_was_submitted(self) -> OperationAttempt:
        if self.started_running_at is not None and self.started_running_at < self.started_at:
            msg = f"attempt {self.attempt} started running at {self.started_running_at}, before it was submitted"
            raise ValueError(msg)
        return self

    @property
    def finished(self) -> bool:
        """Return whether the attempt has an outcome."""
        return self.status not in (OperationRunStatus.QUEUED, OperationRunStatus.RUNNING)
