"""Define the CreateTableMaintenanceRunsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    SpecFilter,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRun, TriggerType
from context.table_maintenance.application.exceptions import ConflictError, NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunsUseCase,
    CreateTableMaintenanceRunsUseCaseInput,
    CreateTableMaintenanceRunsUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )


class CreateTableMaintenanceRunsService(CreateTableMaintenanceRunsUseCase):
    """Create the runs of one plan, one per planned operation, all or none."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, tables_repo: TablesRepo) -> None:
        """Bind the repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(self, request: CreateTableMaintenanceRunsUseCaseInput) -> CreateTableMaintenanceRunsUseCaseOutput:
        """Create the plan's pending runs together, or return them when a first try already stored every one.

        Every run is built before any is stored, and all are stored in one batch, so a run that is refused,
        by the domain or by the store, leaves none of them stored. ``run_ids`` and ``now`` come from the
        caller, so a workflow can supply deterministic values: a retry whose first try stored the runs finds
        every id stored, for the same table and operation, and returns their ids without storing anything.
        A retry that read no run but whose insert meets runs stored meanwhile (a slow first try racing it)
        reads them back and returns them when every one is stored as planned. Some ids stored and others not,
        or a stored run of another table or operation, is a ``ConflictError``, since no try of this request
        leaves that behind.
        """
        with translate_domain_errors():
            trigger = TriggerType(request.trigger)
            priority = TablePriority(request.priority)
            planned = [(TableMaintenanceRunId(run.run_id), run) for run in request.runs]
            stored = [(run, self._runs_repo.get(run_id)) for run_id, run in planned]
            if any(existing is not None for _, existing in stored):
                self._require_stored_as_planned(request, stored)
            else:
                table_uuid = TableId(request.table_uuid)
                table = self._tables_repo.get(table_uuid)
                if table is None:
                    raise NotFoundError(f"table {request.table_uuid} not found")
                runs = [
                    TableMaintenanceRun.create(
                        run_id,
                        table_uuid,
                        trigger,
                        MaintenanceOperation(run.operation),
                        request.now,
                        execution_ref=request.execution_ref,
                        priority=priority,
                        filters=[SpecFilter(spec_id=f.spec_id, where=f.where) for f in run.filters],
                        procedure_args=run.procedure_args,
                    )
                    for run_id, run in planned
                ]
                try:
                    self._runs_repo.create_all(runs)
                except ConflictError:
                    # The insert met runs stored since the reads: they are taken only when they are this plan's.
                    self._require_stored_as_planned(
                        request, [(run, self._runs_repo.get(run_id)) for run_id, run in planned]
                    )
                    return CreateTableMaintenanceRunsUseCaseOutput(run_ids=tuple(run_id.value for run_id, _ in planned))
                if trigger is TriggerType.MANUAL:
                    self._clear_needs_attention(table, [run.operation for run in runs], request.now)
        return CreateTableMaintenanceRunsUseCaseOutput(run_ids=tuple(run_id.value for run_id, _ in planned))

    @staticmethod
    def _require_stored_as_planned(
        request: CreateTableMaintenanceRunsUseCaseInput,
        stored: list[tuple[CreateTableMaintenanceRunsUseCaseInput.Run, TableMaintenanceRun | None]],
    ) -> None:
        """Refuse a plan whose runs are not all stored already, each for the table and the operation planned."""
        table_uuid = TableId(request.table_uuid)
        for run, existing in stored:
            if existing is None:
                raise ConflictError(f"maintenance run {run.run_id} was not created with the rest of its plan")
            if existing.table_uuid != table_uuid or existing.operation is not MaintenanceOperation(run.operation):
                raise ConflictError(f"maintenance run {run.run_id} already exists for another table or operation")

    def _clear_needs_attention(self, table: Table, operations: list[MaintenanceOperation], now: datetime) -> None:
        """Lift the needs-attention mark of each run's operation, saving the table once: a person asked for these runs.

        A dropped table keeps its state, as every other change to it is refused.
        """
        if table.status is TableStatus.DROPPED:
            return
        marked = [op for op in operations if table.operation_state(op).attention is not None]
        for operation in marked:
            table.clear_needs_attention(operation, now)
        if marked:
            self._tables_repo.update(table)
