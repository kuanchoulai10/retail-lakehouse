"""Define the QueuedRunStatus class."""

from __future__ import annotations

from typing import ClassVar

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.status.cancelled_run_status import (
    CancelledRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.failed_run_status import (
    FailedRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.retry_waiting_run_status import (
    RetryWaitingRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.running_run_status import (
    RunningRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.succeeded_run_status import (
    SucceededRunStatus,
)


class QueuedRunStatus(ValueObject, RunStatus):
    """A run whose attempt is submitted and waits for compute."""

    name: ClassVar[RunStatusName] = RunStatusName.QUEUED
    is_in_flight: ClassVar[bool] = True

    def mark_running(self) -> RunStatus:
        """The attempt runs."""
        return RunningRunStatus()

    def succeed(self) -> RunStatus:
        """The attempt succeeded before it was seen running."""
        return SucceededRunStatus()

    def fail(self, *, retries: bool) -> RunStatus:
        """The attempt failed: the run waits to retry when ``retries``, otherwise it failed."""
        return RetryWaitingRunStatus() if retries else FailedRunStatus()

    def cancel(self) -> RunStatus:
        """Cancel the run and its queued attempt."""
        return CancelledRunStatus()
