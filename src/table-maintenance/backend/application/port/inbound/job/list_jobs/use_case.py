"""Define the ListJobsUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from application.port.inbound.job.list_jobs.input import ListJobsInput
from application.port.inbound.job.list_jobs.output import ListJobsOutput


class ListJobsUseCase(UseCase[ListJobsInput, ListJobsOutput]):
    """List all table maintenance jobs."""
