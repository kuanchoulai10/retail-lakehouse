"""Provide the job_to_values serializer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.job import Job


def job_to_values(job: Job) -> dict[str, Any]:
    """Convert a Job domain entity to a dict of SQL column values."""
    return {
        "id": job.id.value,
        "job_type": job.job_type.value,
        "catalog": job.table_ref.catalog,
        "table": job.table_ref.table,
        "job_config": job.job_config,
        "cron": job.cron.expression if job.cron else None,
        "status": job.status.value,
        "next_run_at": job.next_run_at,
        "max_active_runs": job.max_active_runs,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
