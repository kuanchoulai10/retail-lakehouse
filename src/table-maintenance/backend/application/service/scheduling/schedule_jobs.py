"""Define the ScheduleJobsService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from application.domain.model.job_run import TriggerType
from application.port.inbound.scheduling.schedule_jobs import (
    ScheduleJobsResult,
    ScheduleJobsUseCase,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from application.service.outbox.event_serializer import EventSerializer
    from application.port.outbound.event_outbox.event_outbox_store import (
        EventOutboxStore,
    )
    from application.port.outbound.job.jobs_repo import JobsRepo
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

logger = logging.getLogger(__name__)


class ScheduleJobsService(ScheduleJobsUseCase):
    """Create JobRuns for jobs whose cron schedule is due."""

    def __init__(
        self,
        jobs_repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        clock: Callable[[], datetime],
        outbox_repo: EventOutboxStore,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with repo dependencies, clock, outbox repo, and serializer."""
        self._jobs_repo = jobs_repo
        self._job_runs_repo = job_runs_repo
        self._clock = clock
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self, request: None = None) -> ScheduleJobsResult:
        """Run one scheduling tick: find due jobs and write trigger events to outbox."""
        now = self._clock()
        jobs = self._jobs_repo.list_schedulable(now)
        triggered: list[str] = []

        for job in jobs:
            active = self._job_runs_repo.count_active_for_job(job.id)
            try:
                job.trigger(
                    active_run_count=active,
                    trigger_type=TriggerType.SCHEDULED,
                )
                entries = self._serializer.to_outbox_entries(
                    events=job.collect_events(),
                    aggregate_type="Job",
                    aggregate_id=job.id.value,
                )
                self._outbox_repo.save(entries)
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
