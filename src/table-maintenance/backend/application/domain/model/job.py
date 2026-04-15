from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from application.domain.model.job_id import JobId

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job_status import JobStatus
    from application.domain.model.job_type import JobType


@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    """A table maintenance job — the aggregate root of the jobs context."""

    id: JobId
    job_type: JobType
    status: JobStatus
    created_at: datetime
    catalog: str = ""
    table: str = ""
    job_config: dict | None = None
    cron: str | None = None

    def __post_init__(self) -> None:
        if self.job_config is None:
            self.job_config = {}
