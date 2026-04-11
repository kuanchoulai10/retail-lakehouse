from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from base.aggregate_root import AggregateRoot

from jobs.domain.job_id import JobId
from jobs.domain.job_status import JobStatus
from jobs.domain.job_type import JobType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context."""

    id: JobId
    job_type: JobType
    status: JobStatus
    created_at: datetime
