"""Define the GetMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.exceptions import NotFoundError
from application.port.inbound.maintenance_run.get_maintenance_run import (
    GetMaintenanceRunUseCase,
    GetMaintenanceRunUseCaseInput,
    GetMaintenanceRunUseCaseOutput,
)
from application.service.maintenance_run.maintenance_run_output_fields import (
    maintenance_run_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )


class GetMaintenanceRunService(GetMaintenanceRunUseCase):
    """Get one maintenance run."""

    def __init__(self, runs_repo: MaintenanceRunsRepo) -> None:
        """Bind the repo."""
        self._runs_repo = runs_repo

    def execute(
        self, request: GetMaintenanceRunUseCaseInput
    ) -> GetMaintenanceRunUseCaseOutput:
        """Return the run or raise NotFoundError."""
        run = self._runs_repo.get(MaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        return GetMaintenanceRunUseCaseOutput(**maintenance_run_output_fields(run))
