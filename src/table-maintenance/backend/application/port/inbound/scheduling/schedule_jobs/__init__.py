"""ScheduleJobs use case definition."""

from application.port.inbound.scheduling.schedule_jobs.output import (
    ScheduleJobsResult,
)
from application.port.inbound.scheduling.schedule_jobs.use_case import (
    ScheduleJobsUseCase,
)

__all__ = ["ScheduleJobsResult", "ScheduleJobsUseCase"]
