"""Define the RaiseTableMaintenanceRunPriorityService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TablePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RaiseTableMaintenanceRunPriorityUseCase,
    RaiseTableMaintenanceRunPriorityUseCaseInput,
    RaiseTableMaintenanceRunPriorityUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRun
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo


class RaiseTableMaintenanceRunPriorityService(RaiseTableMaintenanceRunPriorityUseCase):
    """Raise the priority of a maintenance run that has not ended, only upward, as a manual run asks."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, tables_repo: TablesRepo) -> None:
        """Bind the runs and tables repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(
        self, request: RaiseTableMaintenanceRunPriorityUseCaseInput
    ) -> RaiseTableMaintenanceRunPriorityUseCaseOutput:
        """Raise the run to the priority asked for, or to its table's priority when none is named.

        A pending run, a run in flight and a failed run with a retry to follow take the raise. The run is
        saved only when it was raised: an equal or lower priority, a run that has ended, or no priority for a
        table that no longer exists changes nothing.
        """
        try:
            asked = None if request.priority is None else TablePriority(request.priority)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        priority = asked if asked is not None else self._table_priority(run)
        with translate_domain_errors():
            raised = priority is not None and run.raise_priority(priority)
            if raised:
                self._runs_repo.update(run)
        return RaiseTableMaintenanceRunPriorityUseCaseOutput(priority=run.priority.value, raised=raised)

    def _table_priority(self, run: TableMaintenanceRun) -> TablePriority | None:
        """Return the current priority of the run's table, or None when the table is gone."""
        table = self._tables_repo.get(run.table_uuid)
        return None if table is None else table.priority
