from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from configs.base import JobType
from pydantic import BaseModel


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


_STATE_MAP: dict[str, JobStatus] = {
    "RUNNING": JobStatus.RUNNING,
    "COMPLETED": JobStatus.COMPLETED,
    "FAILED": JobStatus.FAILED,
    "SUBMISSION_FAILED": JobStatus.FAILED,
    "INVALIDATING": JobStatus.FAILED,
}


def status_from_k8s(kind: str, state: str) -> JobStatus:
    if kind == "ScheduledSparkApplication":
        return JobStatus.RUNNING
    if not state:
        return JobStatus.PENDING
    return _STATE_MAP.get(state, JobStatus.UNKNOWN)


class JobResponse(BaseModel):
    name: str
    kind: str
    namespace: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
