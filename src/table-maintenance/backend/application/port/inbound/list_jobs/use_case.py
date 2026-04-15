from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.list_jobs.input import ListJobsInput
from application.port.inbound.list_jobs.output import ListJobsOutput


class ListJobsUseCase(UseCase[ListJobsInput, ListJobsOutput]):
    """List all table maintenance jobs."""
