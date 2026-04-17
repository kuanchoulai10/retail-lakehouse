from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobRunApiResponse(BaseModel):
    run_id: str
    job_id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
