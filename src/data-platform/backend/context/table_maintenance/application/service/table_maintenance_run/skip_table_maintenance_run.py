"""Define the SkipTableMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    RunStatus,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    SkipTableMaintenanceRunUseCase,
    SkipTableMaintenanceRunUseCaseInput,
    SkipTableMaintenanceRunUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )


class SkipTableMaintenanceRunService(SkipTableMaintenanceRunUseCase):
    """Skip a maintenance run that never started, saying why."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the runs repo."""
        self._runs_repo = runs_repo

    def execute(self, request: SkipTableMaintenanceRunUseCaseInput) -> SkipTableMaintenanceRunUseCaseOutput:
        """Skip the run when it is still pending, and say whether it was skipped.

        A run in any other status (started, finished, or already skipped) is left alone and not saved, so a
        retried skip whose first try landed does not fail.
        """
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        skipped = run.status is RunStatus.PENDING
        if skipped:
            with translate_domain_errors():
                run.skip(request.reason, request.now)
                self._runs_repo.update(run)
        return SkipTableMaintenanceRunUseCaseOutput(run_id=run.id.value, status=run.status.value, skipped=skipped)
