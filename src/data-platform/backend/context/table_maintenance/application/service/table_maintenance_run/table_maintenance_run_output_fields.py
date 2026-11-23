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
        "size": attempt.size.value,
        "status": attempt.status.value,
        "job_name": attempt.job_name,
        "started_at": attempt.started_at,
        "started_running_at": attempt.started_running_at,
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
        "priority": run.priority.value,
        "operation": run.operation.value,
        "status": run.status.value,
        "content": run.content.to_primitives(),
        "metrics": dict(run.metrics),
        "error": run.error,
        "skip_reason": run.skip_reason,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "attempts": tuple(_attempt_fields(a) for a in run.attempts),
    }
