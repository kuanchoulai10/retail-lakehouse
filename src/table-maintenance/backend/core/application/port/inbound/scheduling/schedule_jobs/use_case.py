"""Define the ScheduleJobsUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from core.application.port.inbound.scheduling.schedule_jobs.output import (
    ScheduleJobsResult,
)


class ScheduleJobsUseCase(UseCase[None, ScheduleJobsResult]):
    """Run one scheduling tick: find due jobs and trigger them."""
