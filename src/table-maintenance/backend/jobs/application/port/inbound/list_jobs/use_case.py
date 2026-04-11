from __future__ import annotations

from base.use_case import UseCase

from jobs.application.port.inbound.list_jobs.input import ListJobsInput
from jobs.application.port.inbound.list_jobs.output import ListJobsOutput


class ListJobsUseCase(UseCase[ListJobsInput, ListJobsOutput]):
    """List all table maintenance jobs."""
