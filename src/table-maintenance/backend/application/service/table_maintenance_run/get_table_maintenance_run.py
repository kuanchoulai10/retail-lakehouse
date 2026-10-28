"""Define the GetTableMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table_maintenance_run.table_maintenance_run_id import (
    TableMaintenanceRunId,
)
from application.exceptions import NotFoundError
from application.port.inbound.table_maintenance_run.get_table_maintenance_run import (
    GetTableMaintenanceRunUseCase,
    GetTableMaintenanceRunUseCaseInput,
    GetTableMaintenanceRunUseCaseOutput,
)
from application.service.table_maintenance_run.table_maintenance_run_output_fields import (
    table_maintenance_run_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.table_maintenance_runs_repo import (
        TableMaintenanceRunsRepo,
    )


class GetTableMaintenanceRunService(GetTableMaintenanceRunUseCase):
    """Get one maintenance run."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the repo."""
        self._runs_repo = runs_repo

    def execute(
        self, request: GetTableMaintenanceRunUseCaseInput
    ) -> GetTableMaintenanceRunUseCaseOutput:
        """Return the run or raise NotFoundError."""
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        return GetTableMaintenanceRunUseCaseOutput(
            **table_maintenance_run_output_fields(run)
        )
