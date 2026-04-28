"""Provide the row_to_job_run deserializer."""

from __future__ import annotations

from typing import Any

from application.domain.model.job import JobId
from application.domain.model.job_run import (
    JobRun,
    JobRunId,
    JobRunStatus,
    TriggerType,
)
from application.domain.model.job_run.job_run_result import JobRunResult


def row_to_job_run(row: Any) -> JobRun:
    """Convert a SQL row to a JobRun domain entity."""
    result = None
    if row["result_duration_ms"] is not None or row["result_metadata"] is not None:
        result = JobRunResult(
            duration_ms=row["result_duration_ms"],
            metadata=row["result_metadata"] or {},
        )
    return JobRun(
        id=JobRunId(value=row["id"]),
        job_id=JobId(value=row["job_id"]),
        status=JobRunStatus(row["status"]),
        trigger_type=TriggerType(row["trigger_type"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        error=row["error"],
        result=result,
    )
