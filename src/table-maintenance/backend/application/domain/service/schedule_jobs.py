"""Define the ScheduleJobsService."""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId
from application.domain.service.schedule_jobs_result import ScheduleJobsResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from application.port.outbound.job.jobs_repo import JobsRepo
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

logger = logging.getLogger(__name__)


class ScheduleJobsService:
    """Create JobRuns for jobs whose cron schedule is due."""

    def __init__(
        self,
        jobs_repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize with repo dependencies and a clock function."""
        self._jobs_repo = jobs_repo
        self._job_runs_repo = job_runs_repo
        self._clock = clock

    def execute(self) -> ScheduleJobsResult:
        """Run one scheduling tick: find due jobs and create pending runs."""
        now = self._clock()
        jobs = self._jobs_repo.list_schedulable(now)
        triggered: list[str] = []

        for job in jobs:
            active = self._job_runs_repo.count_active_for_job(job.id)
            try:
                run = job.trigger(
                    run_id=JobRunId(value=f"{job.id.value}-{secrets.token_hex(3)}"),
                    now=now,
                    active_run_count=active,
                )
                self._job_runs_repo.create(run)
                assert job.cron is not None  # guaranteed by list_schedulable
                next_time = job.cron.next_run_after(now)
                self._jobs_repo.save_next_run_at(job.id, next_time)
                triggered.append(job.id.value)
            except Exception:
                logger.exception("Failed to schedule job %s", job.id.value)

        return ScheduleJobsResult(
            triggered_count=len(triggered),
            job_ids=triggered,
        )
