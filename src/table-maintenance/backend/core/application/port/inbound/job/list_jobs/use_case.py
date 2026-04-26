"""Define the ListJobsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from core.application.port.inbound.job.list_jobs.input import ListJobsInput
from core.application.port.inbound.job.list_jobs.output import ListJobsOutput


class ListJobsUseCase(UseCase[ListJobsInput, ListJobsOutput]):
    """List all table maintenance jobs."""
