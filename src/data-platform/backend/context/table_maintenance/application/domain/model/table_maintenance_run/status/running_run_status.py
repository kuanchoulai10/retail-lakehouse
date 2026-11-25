"""Define the RunningRunStatus class."""

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
from context.table_maintenance.application.domain.model.table_maintenance_run.status.succeeded_run_status import (
    SucceededRunStatus,
)


class RunningRunStatus(ValueObject, RunStatus):
    """A run whose attempt is running."""

    name: ClassVar[RunStatusName] = RunStatusName.RUNNING
    is_in_flight: ClassVar[bool] = True

    def succeed(self) -> RunStatus:
        """The attempt succeeded."""
        return SucceededRunStatus()

    def fail(self, *, retries: bool) -> RunStatus:
        """The attempt failed: the run waits to retry when ``retries``, otherwise it failed."""
        return RetryWaitingRunStatus() if retries else FailedRunStatus()

    def cancel(self) -> RunStatus:
        """Cancel the run and its running attempt."""
        return CancelledRunStatus()
