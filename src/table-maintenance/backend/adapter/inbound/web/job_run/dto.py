"""Define JobRun API response DTO."""

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
