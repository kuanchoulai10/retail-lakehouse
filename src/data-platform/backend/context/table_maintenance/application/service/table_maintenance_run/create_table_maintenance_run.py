"""Define the CreateTableMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunUseCase,
    CreateTableMaintenanceRunUseCaseInput,
    CreateTableMaintenanceRunUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_run.table_maintenance_run_output_fields import (
    table_maintenance_run_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )


class CreateTableMaintenanceRunService(CreateTableMaintenanceRunUseCase):
    """Create the run that tracks one execution of maintenance operations."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, tables_repo: TablesRepo) -> None:
        """Bind the repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(self, request: CreateTableMaintenanceRunUseCaseInput) -> CreateTableMaintenanceRunUseCaseOutput:
        """Create the run, or return the existing one when the id is already used.

        ``run_id`` and ``now`` come from the caller so a workflow can supply
        deterministic values and retry safely.
        """
        if not request.operations:
            raise ValidationError("operations must not be empty")
        with translate_domain_errors():
            trigger = TriggerType(request.trigger)
            operations = [MaintenanceOperation(op) for op in request.operations]
            run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
            if run is None:
                table_uuid = TableId(request.table_uuid)
                if self._tables_repo.get(table_uuid) is None:
                    raise NotFoundError(f"table {request.table_uuid} not found")
                run = self._runs_repo.create(
                    TableMaintenanceRun.create(
                        TableMaintenanceRunId(request.run_id),
                        table_uuid,
                        trigger,
                        operations,
                        request.now,
                        execution_ref=request.execution_ref,
                    )
                )
        return CreateTableMaintenanceRunUseCaseOutput(**table_maintenance_run_output_fields(run))
