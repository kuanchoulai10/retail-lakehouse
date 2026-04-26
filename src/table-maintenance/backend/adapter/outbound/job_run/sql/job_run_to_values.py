"""Provide the job_run_to_values serializer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.job_run import JobRun


def job_run_to_values(run: JobRun) -> dict[str, Any]:
    """Convert a JobRun domain entity to a dict of SQL column values."""
    return {
        "id": run.id.value,
        "job_id": run.job_id.value,
        "status": run.status.value,
        "trigger_type": run.trigger_type.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
