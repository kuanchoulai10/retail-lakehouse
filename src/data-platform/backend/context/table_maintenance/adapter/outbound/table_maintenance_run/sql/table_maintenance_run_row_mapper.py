"""Define the TableMaintenanceRunRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.outbound.shared.sql import IsoDatetimeCodec
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ComputeSize,
    FailureClass,
    MaintenanceOperation,
    NextStep,
    OperationAttempt,
    OperationRun,
    OperationRunStatus,
    TableId,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TablePriority,
    TriggerType,
)

if TYPE_CHECKING:
    from enum import StrEnum

    from sqlalchemy import RowMapping


def _value(member: StrEnum | None) -> str | None:
    return member.value if member is not None else None


def _encode_attempt(attempt: OperationAttempt) -> dict[str, Any]:
    return {
        "attempt": attempt.attempt,
        "size": _value(attempt.size),
        "status": attempt.status.value,
        "started_at": IsoDatetimeCodec.encode(attempt.started_at),
        "finished_at": IsoDatetimeCodec.encode(attempt.finished_at),
        "failure_class": _value(attempt.failure_class),
        "error": attempt.error,
        "event_log_finished": attempt.event_log_finished,
        "next_step": _value(attempt.next_step),
        "next_size": _value(attempt.next_size),
    }


def _decode_attempt(data: dict[str, Any]) -> OperationAttempt:
    size, failure_class, next_step, next_size = (
        data.get("size"),
        data.get("failure_class"),
        data.get("next_step"),
        data.get("next_size"),
    )
    started_at = IsoDatetimeCodec.decode(data["started_at"])
    if started_at is None:
        msg = f"attempt {data['attempt']} has no start time"
        raise ValueError(msg)
    return OperationAttempt(
        attempt=data["attempt"],
        size=ComputeSize(size) if size is not None else None,
        status=OperationRunStatus(data["status"]),
        started_at=started_at,
        finished_at=IsoDatetimeCodec.decode(data.get("finished_at")),
        failure_class=FailureClass(failure_class) if failure_class is not None else None,
        error=data.get("error"),
        event_log_finished=data.get("event_log_finished"),
        next_step=NextStep(next_step) if next_step is not None else None,
        next_size=ComputeSize(next_size) if next_size is not None else None,
    )


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
        "attempt_history": [_encode_attempt(a) for a in op.attempt_history],
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
        attempt_history=tuple(_decode_attempt(a) for a in data.get("attempt_history", [])),
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
            "priority": run.priority.value,
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
            priority=TablePriority(row["priority"] or TablePriority.default()),
        )
