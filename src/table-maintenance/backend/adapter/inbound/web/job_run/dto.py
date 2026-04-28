"""Define JobRun API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobRunApiResponse(BaseModel):
    """Response body representing a job run."""

    run_id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None = None
    result_duration_ms: int | None = None
    result_metadata: dict[str, str] | None = None


class CompleteJobRunApiRequest(BaseModel):
    """Request body for completing a job run."""

    duration_ms: int | None = None
    metadata: dict[str, str] | None = None


class FailJobRunApiRequest(BaseModel):
    """Request body for failing a job run."""

    error: str
    duration_ms: int | None = None
    metadata: dict[str, str] | None = None


class JobRunCallbackApiResponse(BaseModel):
    """Response body after a callback state transition."""

    run_id: str
    status: str
    finished_at: datetime
