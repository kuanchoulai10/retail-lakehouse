"""Define the TableMaintenanceRunRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.outbound.shared.sql import IsoDatetimeCodec
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    AttemptStatus,
    ComputeSize,
    FailureClass,
    MaintenanceOperation,
    NextStep,
    OperationAttempt,
    RunStatus,
    TableId,
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TablePriority,
    TriggerType,
    maintenance_job_content_from_primitives,
)

if TYPE_CHECKING:
    from enum import StrEnum

    from sqlalchemy import RowMapping


def _value(member: StrEnum | None) -> str | None:
    return member.value if member is not None else None


def _encode_attempt(attempt: OperationAttempt) -> dict[str, Any]:
    return {
        "attempt": attempt.attempt,
        "size": attempt.size.value,
        "status": attempt.status.value,
        "job_name": attempt.job_name,
        "started_at": IsoDatetimeCodec.encode(attempt.started_at),
        "started_running_at": IsoDatetimeCodec.encode(attempt.started_running_at),
        "finished_at": IsoDatetimeCodec.encode(attempt.finished_at),
        "failure_class": _value(attempt.failure_class),
        "error": attempt.error,
        "event_log_finished": attempt.event_log_finished,
        "next_step": _value(attempt.next_step),
        "next_size": _value(attempt.next_size),
    }


def _decode_attempt(data: dict[str, Any]) -> OperationAttempt:
    failure_class, next_step, next_size = data["failure_class"], data["next_step"], data["next_size"]
    started_at = IsoDatetimeCodec.decode(data["started_at"])
    if started_at is None:
        msg = f"attempt {data['attempt']} has no start time"
        raise ValueError(msg)
    return OperationAttempt(
        attempt=data["attempt"],
        size=ComputeSize(data["size"]),
        status=AttemptStatus(data["status"]),
        started_at=started_at,
        job_name=data["job_name"],
        started_running_at=IsoDatetimeCodec.decode(data["started_running_at"]),
        finished_at=IsoDatetimeCodec.decode(data["finished_at"]),
        failure_class=FailureClass(failure_class) if failure_class is not None else None,
        error=data["error"],
        event_log_finished=data["event_log_finished"],
        next_step=NextStep(next_step) if next_step is not None else None,
        next_size=ComputeSize(next_size) if next_size is not None else None,
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
            "operation": run.operation.value,
            "priority": run.priority.value,
            "status": run.status.value,
            "error": run.error,
            "skip_reason": run.skip_reason,
            "content_json": run.content.to_primitives(),
            "metrics_json": dict(run.metrics),
            "attempts_json": [_encode_attempt(a) for a in run.attempts],
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
            operation=MaintenanceOperation(row["operation"]),
            created_at=row["created_at"],
            execution_ref=row["execution_ref"],
            priority=TablePriority(row["priority"]),
            status=RunStatus(row["status"]),
            content=maintenance_job_content_from_primitives(row["content_json"]),
            metrics=dict(row["metrics_json"]),
            error=row["error"],
            skip_reason=row["skip_reason"],
            finished_at=row["finished_at"],
            attempts=tuple(_decode_attempt(a) for a in row["attempts_json"]),
        )
