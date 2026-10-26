"""Define the MaintenanceRunRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.sql.iso_datetime_codec import IsoDatetimeCodec
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.maintenance_run.operation_run import OperationRun
from application.domain.model.maintenance_run.operation_run_status import (
    OperationRunStatus,
)
from application.domain.model.maintenance_run.trigger_type import TriggerType
from application.domain.model.managed_table.table_uuid import TableUuid

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


def _encode_operation(op: OperationRun) -> dict[str, Any]:
    return {
        "operation": op.operation.value,
        "status": op.status.value,
        "attempts": op.attempts,
        "started_at": IsoDatetimeCodec.encode(op.started_at),
        "finished_at": IsoDatetimeCodec.encode(op.finished_at),
        "spark_application": op.spark_application,
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
        spark_application=data["spark_application"],
        metrics=dict(data["metrics"]),
        error=data["error"],
        expected_files=data["expected_files"],
    )


class MaintenanceRunRowMapper:
    """Convert between MaintenanceRun aggregates and table rows."""

    @staticmethod
    def to_values(run: MaintenanceRun) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": run.id.value,
            "table_uuid": run.table_uuid.value,
            "workflow_id": run.workflow_id,
            "trigger": run.trigger.value,
            "operations_json": [_encode_operation(op) for op in run.operations],
            "created_at": run.created_at,
            "finished_at": run.finished_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> MaintenanceRun:
        """Rebuild the aggregate from a row without registering events."""
        return MaintenanceRun(
            id=MaintenanceRunId(row["id"]),
            table_uuid=TableUuid(row["table_uuid"]),
            trigger=TriggerType(row["trigger"]),
            operations=tuple(_decode_operation(d) for d in row["operations_json"]),
            created_at=row["created_at"],
            workflow_id=row["workflow_id"],
            finished_at=row["finished_at"],
        )
