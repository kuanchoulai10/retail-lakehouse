"""Define the ListTableMaintenanceRunsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    ListTableMaintenanceRunsUseCase,
    ListTableMaintenanceRunsUseCaseInput,
    ListTableMaintenanceRunsUseCaseOutput,
    ListTableMaintenanceRunsUseCaseOutputItem,
)
from context.table_maintenance.application.service.table_maintenance_run.table_maintenance_run_output_fields import (
    table_maintenance_run_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )


class ListTableMaintenanceRunsService(ListTableMaintenanceRunsUseCase):
    """List the maintenance runs of a table, newest first."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the repo."""
        self._runs_repo = runs_repo

    def execute(self, request: ListTableMaintenanceRunsUseCaseInput) -> ListTableMaintenanceRunsUseCaseOutput:
        """Return up to ``limit`` runs of the table."""
        runs = self._runs_repo.list_by_table(TableId(request.table_uuid), request.limit)
        return ListTableMaintenanceRunsUseCaseOutput(
            items=[
                ListTableMaintenanceRunsUseCaseOutputItem(**table_maintenance_run_output_fields(run)) for run in runs
            ]
        )
