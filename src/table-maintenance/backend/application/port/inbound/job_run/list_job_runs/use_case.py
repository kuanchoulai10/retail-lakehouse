"""Define the ListJobRunsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.list_job_runs.input import ListJobRunsUseCaseInput
from application.port.inbound.job_run.list_job_runs.output import (
    ListJobRunsUseCaseOutput,
)


class ListJobRunsUseCase(UseCase[ListJobRunsUseCaseInput, ListJobRunsUseCaseOutput]):
    """List all JobRuns associated with a Job."""
