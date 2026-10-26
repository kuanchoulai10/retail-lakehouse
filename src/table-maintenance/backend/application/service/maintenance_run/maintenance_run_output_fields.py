"""Define the maintenance_run_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun


def maintenance_run_output_fields(run: MaintenanceRun) -> dict[str, Any]:
    """Return the primitive fields shared by every maintenance run output."""
    return {
        "run_id": run.id.value,
        "table_uuid": run.table_uuid.value,
        "workflow_id": run.workflow_id,
        "trigger": run.trigger.value,
        "status": run.status.value,
        "operations": [
            {
                "operation": op.operation.value,
                "status": op.status.value,
                "attempts": op.attempts,
                "started_at": op.started_at,
                "finished_at": op.finished_at,
                "spark_application": op.spark_application,
                "metrics": dict(op.metrics),
                "error": op.error,
                "expected_files": op.expected_files,
            }
            for op in run.operations
        ],
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }
