from __future__ import annotations

from typing import Any

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus


def row_to_job_run(row: Any) -> JobRun:
    return JobRun(
        id=JobRunId(value=row["id"]),
        job_id=JobId(value=row["job_id"]),
        status=JobRunStatus(row["status"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )
