"""Define the table_maintenance_run_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from enum import StrEnum

    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        OperationAttempt,
        TableMaintenanceRun,
    )


def _value(member: StrEnum | None) -> str | None:
    return member.value if member is not None else None


def _attempt_fields(attempt: OperationAttempt) -> dict[str, Any]:
    return {
        "attempt": attempt.attempt,
        "size": _value(attempt.size),
        "status": attempt.status.value,
        "started_at": attempt.started_at,
        "finished_at": attempt.finished_at,
        "failure_class": _value(attempt.failure_class),
        "error": attempt.error,
        "event_log_finished": attempt.event_log_finished,
        "next_step": _value(attempt.next_step),
        "next_size": _value(attempt.next_size),
    }


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
                "attempt_history": [_attempt_fields(a) for a in op.attempt_history],
            }
            for op in run.operations
        ],
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }
