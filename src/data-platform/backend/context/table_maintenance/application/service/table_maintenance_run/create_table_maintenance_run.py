"""Define the CreateTableMaintenanceRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    SpecFilter,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import TableId, TableStatus
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import NotFoundError
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
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )


class CreateTableMaintenanceRunService(CreateTableMaintenanceRunUseCase):
    """Create the run that tracks one maintenance operation against a table."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, tables_repo: TablesRepo) -> None:
        """Bind the repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(self, request: CreateTableMaintenanceRunUseCaseInput) -> CreateTableMaintenanceRunUseCaseOutput:
        """Create the pending run, or return the existing one when the id is already used.

        ``run_id`` and ``now`` come from the caller so a workflow can supply
        deterministic values and retry safely.
        """
        with translate_domain_errors():
            trigger = TriggerType(request.trigger)
            priority = TablePriority(request.priority)
            operation = MaintenanceOperation(request.operation)
            filters = [SpecFilter(spec_id=f.spec_id, where=f.where) for f in request.filters]
            run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
            if run is None:
                table_uuid = TableId(request.table_uuid)
                table = self._tables_repo.get(table_uuid)
                if table is None:
                    raise NotFoundError(f"table {request.table_uuid} not found")
                run = self._runs_repo.create(
                    TableMaintenanceRun.create(
                        TableMaintenanceRunId(request.run_id),
                        table_uuid,
                        trigger,
                        operation,
                        request.now,
                        execution_ref=request.execution_ref,
                        priority=priority,
                        filters=filters,
                        procedure_args=request.procedure_args,
                    )
                )
                if trigger is TriggerType.MANUAL:
                    self._clear_needs_attention(table, operation, request.now)
        return CreateTableMaintenanceRunUseCaseOutput(**table_maintenance_run_output_fields(run))

    def _clear_needs_attention(self, table: Table, operation: MaintenanceOperation, now: datetime) -> None:
        """Lift the needs-attention mark of the run's operation: a person asked for this run.

        A dropped table keeps its state, as every other change to it is refused.
        """
        if table.operation_state(operation).attention is None or table.status is TableStatus.DROPPED:
            return
        table.clear_needs_attention(operation, now)
        self._tables_repo.update(table)
