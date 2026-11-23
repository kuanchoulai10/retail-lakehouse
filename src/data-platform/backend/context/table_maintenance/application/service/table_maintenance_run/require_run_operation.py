"""Define the require_run_operation function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
    from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRun


def require_run_operation(run: TableMaintenanceRun, operation: MaintenanceOperation) -> None:
    """Refuse, as a conflict, a request about ``run`` that names an operation other than the run's own.

    A run does one operation; its jobs and their processes are named by ``(run_id, operation, attempt)``, so a
    request naming another operation would reach jobs the run never had.
    """
    if operation is not run.operation:
        raise ConflictError(f"run {run.id.value} does not run {operation.value}")
