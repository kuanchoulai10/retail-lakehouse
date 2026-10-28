"""Define the CreateMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.maintenance_run.trigger_type import TriggerType
from application.domain.model.table.table_id import TableId
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.maintenance_run.create_maintenance_run import (
    CreateMaintenanceRunUseCase,
    CreateMaintenanceRunUseCaseInput,
    CreateMaintenanceRunUseCaseOutput,
)
from application.service.maintenance_run.maintenance_run_output_fields import (
    maintenance_run_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )


class CreateMaintenanceRunService(CreateMaintenanceRunUseCase):
    """Create the run that tracks one execution of maintenance operations."""

    def __init__(self, runs_repo: MaintenanceRunsRepo, tables_repo: TablesRepo) -> None:
        """Bind the repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(
        self, request: CreateMaintenanceRunUseCaseInput
    ) -> CreateMaintenanceRunUseCaseOutput:
        """Create the run, or return the existing one when the id is already used.

        ``run_id`` and ``now`` come from the caller so a workflow can supply
        deterministic values and retry safely.
        """
        if not request.operations:
            raise ValidationError("operations must not be empty")
        with translate_domain_errors():
            trigger = TriggerType(request.trigger)
            operations = [MaintenanceOperation(op) for op in request.operations]
            run = self._runs_repo.get(MaintenanceRunId(request.run_id))
            if run is None:
                table_uuid = TableId(request.table_uuid)
                if self._tables_repo.get(table_uuid) is None:
                    raise NotFoundError(f"table {request.table_uuid} not found")
                run = self._runs_repo.create(
                    MaintenanceRun.create(
                        MaintenanceRunId(request.run_id),
                        table_uuid,
                        trigger,
                        operations,
                        request.now,
                        workflow_id=request.workflow_id,
                    )
                )
        return CreateMaintenanceRunUseCaseOutput(**maintenance_run_output_fields(run))
