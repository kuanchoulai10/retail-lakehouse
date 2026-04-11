from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from jobs.application.domain.job_id import JobId

if TYPE_CHECKING:
    from datetime import datetime

    from jobs.application.domain.job_status import JobStatus
    from jobs.application.domain.job_type import JobType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context."""

    id: JobId
    job_type: JobType
    status: JobStatus
    created_at: datetime
