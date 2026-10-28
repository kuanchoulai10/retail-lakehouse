"""Define the table_maintenance_run_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.table_maintenance_run import TableMaintenanceRun


def table_maintenance_run_output_fields(run: TableMaintenanceRun) -> dict[str, Any]:
    """Return the primitive fields shared by every maintenance run output."""
    return {
        "run_id": run.id.value,
        "table_uuid": run.table_uuid.value,
        "execution_ref": run.execution_ref,
        "trigger": run.trigger.value,
        "status": run.status.value,
        "operations": [
            {
                "operation": op.operation.value,
                "status": op.status.value,
                "attempts": op.attempts,
                "started_at": op.started_at,
                "finished_at": op.finished_at,
                "job_name": op.job_name,
                "metrics": dict(op.metrics),
                "error": op.error,
                "expected_files": op.expected_files,
            }
            for op in run.operations
        ],
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }
