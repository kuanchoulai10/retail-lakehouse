"""Define the ListJobsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.list_jobs.input import ListJobsUseCaseInput
from application.port.inbound.job.list_jobs.output import ListJobsUseCaseOutput


class ListJobsUseCase(UseCase[ListJobsUseCaseInput, ListJobsUseCaseOutput]):
    """List all table maintenance jobs."""
