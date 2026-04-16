from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from application.domain.model.job_run_id import JobRunId

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job_id import JobId
    from application.domain.model.job_run_status import JobRunStatus


@dataclass(eq=False)
class JobRun(AggregateRoot[JobRunId]):
    """A single execution of a Job — the aggregate root for run history."""

    id: JobRunId
    job_id: JobId
    status: JobRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
