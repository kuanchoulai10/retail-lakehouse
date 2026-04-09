from __future__ import annotations

from datetime import datetime

from configs.base import JobType
from pydantic import BaseModel

from models.job_status import JobStatus


class JobResponse(BaseModel):
    name: str
    kind: str
    namespace: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
