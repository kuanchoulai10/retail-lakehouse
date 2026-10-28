"""Define the TableMaintenanceRunRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.shared.sql import IsoDatetimeCodec
from application.domain.model.shared import MaintenanceOperation
from application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    OperationRun,
    OperationRunStatus,
    TriggerType,
)
from application.domain.model.table import TableId

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


def _encode_operation(op: OperationRun) -> dict[str, Any]:
    return {
        "operation": op.operation.value,
        "status": op.status.value,
        "attempts": op.attempts,
        "started_at": IsoDatetimeCodec.encode(op.started_at),
        "finished_at": IsoDatetimeCodec.encode(op.finished_at),
        "job_name": op.job_name,
        "metrics": dict(op.metrics),
        "error": op.error,
        "expected_files": op.expected_files,
    }


def _decode_operation(data: dict[str, Any]) -> OperationRun:
    return OperationRun(
        operation=MaintenanceOperation(data["operation"]),
        status=OperationRunStatus(data["status"]),
        attempts=data["attempts"],
        started_at=IsoDatetimeCodec.decode(data["started_at"]),
        finished_at=IsoDatetimeCodec.decode(data["finished_at"]),
        job_name=data["job_name"],
        metrics=dict(data["metrics"]),
        error=data["error"],
        expected_files=data["expected_files"],
    )


class TableMaintenanceRunRowMapper:
    """Convert between TableMaintenanceRun aggregates and table rows."""

    @staticmethod
    def to_values(run: TableMaintenanceRun) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": run.id.value,
            "table_uuid": run.table_uuid.value,
            "execution_ref": run.execution_ref,
            "trigger": run.trigger.value,
            "operations_json": [_encode_operation(op) for op in run.operations],
            "created_at": run.created_at,
            "finished_at": run.finished_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableMaintenanceRun:
        """Rebuild the aggregate from a row without registering events."""
        return TableMaintenanceRun(
            id=TableMaintenanceRunId(row["id"]),
            table_uuid=TableId(row["table_uuid"]),
            trigger=TriggerType(row["trigger"]),
            operations=tuple(_decode_operation(d) for d in row["operations_json"]),
            created_at=row["created_at"],
            execution_ref=row["execution_ref"],
            finished_at=row["finished_at"],
        )
