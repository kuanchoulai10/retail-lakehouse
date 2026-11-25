"""Define the RetryWaitingRunStatus class."""

from __future__ import annotations

from typing import ClassVar

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.status.cancelled_run_status import (
    CancelledRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)


class RetryWaitingRunStatus(ValueObject, RunStatus):
    """A run whose attempt failed and that waits to submit its next attempt; it is not finished."""

    name: ClassVar[RunStatusName] = RunStatusName.RETRY_WAITING

    def start_attempt(self) -> RunStatus:
        """Submit the next attempt: the run is queued again."""
        # Imported here: a queued run's failure leads back to this status, so a top-level import would be a cycle.
        from context.table_maintenance.application.domain.model.table_maintenance_run.status.queued_run_status import (  # noqa: E501
            QueuedRunStatus,
        )

        return QueuedRunStatus()

    def cancel(self) -> RunStatus:
        """Cancel the run while it waits to retry."""
        return CancelledRunStatus()
