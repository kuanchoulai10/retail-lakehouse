"""Define the JobRunInMemoryExecutor adapter."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from core.application.port.outbound.job_run.job_run_executor import JobRunExecutor

if TYPE_CHECKING:
    from core.application.domain.model.job import Job


class JobRunInMemoryExecutor(JobRunExecutor):
    """Test double for JobRunExecutor. Records every triggered run."""

    def __init__(self) -> None:
        """Initialize an empty list of triggered runs."""
        self.triggered_runs: list[JobRun] = []

    def trigger(self, job: Job) -> JobRun:
        """Create a pending JobRun in memory and record it."""
        run = JobRun(
            id=JobRunId(value=f"{job.id.value}-{secrets.token_hex(3)}"),
            job_id=job.id,
            status=JobRunStatus.PENDING,
            started_at=datetime.now(UTC),
        )
        self.triggered_runs.append(run)
        return run
