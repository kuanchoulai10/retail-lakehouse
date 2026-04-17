from __future__ import annotations

from typing import Any

from application.domain.model.job import Job, JobId, JobType


def row_to_job(row: Any) -> Job:
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
    )
