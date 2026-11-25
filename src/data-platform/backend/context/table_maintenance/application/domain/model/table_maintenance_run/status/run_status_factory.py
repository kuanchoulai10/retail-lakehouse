"""Define the RunStatusFactory class."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, ClassVar

from context.table_maintenance.application.domain.model.table_maintenance_run.status.cancelled_run_status import (
    CancelledRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.failed_run_status import (
    FailedRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.pending_run_status import (
    PendingRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.queued_run_status import (
    QueuedRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.retry_waiting_run_status import (
    RetryWaitingRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.running_run_status import (
    RunningRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.skipped_run_status import (
    SkippedRunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.succeeded_run_status import (
    SucceededRunStatus,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
        RunStatus,
    )


class RunStatusFactory:
    """Create a run's status from its name, as stored and sent."""

    _BY_NAME: ClassVar[Mapping[RunStatusName, type[RunStatus]]] = MappingProxyType(
        {
            status.name: status
            for status in (
                PendingRunStatus,
                QueuedRunStatus,
                RunningRunStatus,
                RetryWaitingRunStatus,
                SucceededRunStatus,
                FailedRunStatus,
                SkippedRunStatus,
                CancelledRunStatus,
            )
        }
    )

    @classmethod
    def create(cls, name: str) -> RunStatus:
        """Return the status named ``name``; a name that is no run status raises ``ValueError``."""
        return cls._BY_NAME[RunStatusName(name)]()
