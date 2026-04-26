"""Provide the row_to_job deserializer."""

from __future__ import annotations

from typing import Any

from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    ResourceConfig,
    TableReference,
)


def row_to_job(row: Any) -> Job:
    """Convert a SQL row to a Job domain entity."""
    cron_str = row["cron"]
    return Job(
        id=JobId(value=row["id"]),
        job_type=JobType(row["job_type"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        table_ref=TableReference(catalog=row["catalog"], table=row["table"]),
        job_config=row["job_config"],
        cron=CronExpression(expression=cron_str) if cron_str else None,
        status=JobStatus(row["status"]),
        next_run_at=row["next_run_at"],
        max_active_runs=row["max_active_runs"],
        resource_config=ResourceConfig(
            driver_memory=row["driver_memory"],
            executor_memory=row["executor_memory"],
            executor_instances=row["executor_instances"],
        ),
    )
