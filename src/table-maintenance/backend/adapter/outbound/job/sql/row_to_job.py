"""Provide the row_to_job deserializer."""

from __future__ import annotations

from typing import Any

from application.domain.model.job import Job, JobId, JobType


def row_to_job(row: Any) -> Job:
    """Convert a SQL row to a Job domain entity."""
    return Job(
        id=JobId(value=row["id"]),
        job_type=JobType(row["job_type"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        catalog=row["catalog"],
        table=row["table"],
        job_config=row["job_config"],
        cron=row["cron"],
        enabled=row["enabled"],
        next_run_at=row["next_run_at"],
        max_active_runs=row["max_active_runs"],
    )
