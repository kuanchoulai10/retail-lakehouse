"""Define the PendingRunStatus class."""

from __future__ import annotations

from typing import ClassVar

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.status.cancelled_run_status import (
    CancelledRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.queued_run_status import (
    QueuedRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.skipped_run_status import (
    SkippedRunStatus,
)


class PendingRunStatus(ValueObject, RunStatus):
    """A run whose first attempt is not submitted yet."""

    name: ClassVar[RunStatusName] = RunStatusName.PENDING

    def start_attempt(self) -> RunStatus:
        """Submit the first attempt: the run is queued."""
        return QueuedRunStatus()

    def cancel(self) -> RunStatus:
        """Cancel the run before it starts."""
        return CancelledRunStatus()

    def skip(self) -> RunStatus:
        """Skip the run: it never starts."""
        return SkippedRunStatus()
