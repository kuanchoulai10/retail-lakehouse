"""Define the CancelTableMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableMaintenanceRunId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    PendingRunStatus,
    RetryWaitingRunStatus,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CancelTableMaintenanceRunUseCase,
    CancelTableMaintenanceRunUseCaseInput,
    CancelTableMaintenanceRunUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )

_CANCELLABLE = (PendingRunStatus(), RetryWaitingRunStatus())


class CancelTableMaintenanceRunService(CancelTableMaintenanceRunUseCase):
    """Cancel a maintenance run with no attempt in flight: one pending or waiting to retry."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the runs repo."""
        self._runs_repo = runs_repo

    def execute(self, request: CancelTableMaintenanceRunUseCaseInput) -> CancelTableMaintenanceRunUseCaseOutput:
        """Cancel the run when it is pending or waiting to retry, and say whether it was cancelled.

        A run in any other status (an attempt in flight, or ended, already cancelled included) is left alone
        and not saved, so a retried cancel whose first try landed does not fail. A run in flight is cancelled
        through its attempt, when that attempt's cancel is recorded.
        """
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        cancelled = run.status in _CANCELLABLE
        if cancelled:
            with translate_domain_errors():
                run.cancel(request.now)
                self._runs_repo.update(run)
        return CancelTableMaintenanceRunUseCaseOutput(
            run_id=run.id.value, status=run.status.name.value, cancelled=cancelled
        )
