"""Define the ListMaintenanceRunsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table.table_id import TableId
from application.port.inbound.maintenance_run.list_maintenance_runs import (
    ListMaintenanceRunsUseCase,
    ListMaintenanceRunsUseCaseInput,
    ListMaintenanceRunsUseCaseOutput,
    ListMaintenanceRunsUseCaseOutputItem,
)
from application.service.maintenance_run.maintenance_run_output_fields import (
    maintenance_run_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )


class ListMaintenanceRunsService(ListMaintenanceRunsUseCase):
    """List the maintenance runs of a table, newest first."""

    def __init__(self, runs_repo: MaintenanceRunsRepo) -> None:
        """Bind the repo."""
        self._runs_repo = runs_repo

    def execute(
        self, request: ListMaintenanceRunsUseCaseInput
    ) -> ListMaintenanceRunsUseCaseOutput:
        """Return up to ``limit`` runs of the table."""
        runs = self._runs_repo.list_by_table(TableId(request.table_uuid), request.limit)
        return ListMaintenanceRunsUseCaseOutput(
            items=[
                ListMaintenanceRunsUseCaseOutputItem(
                    **maintenance_run_output_fields(run)
                )
                for run in runs
            ]
        )
