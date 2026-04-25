"""Define the ListJobRunsUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from core.application.port.inbound.job_run.list_job_runs.input import ListJobRunsInput
from core.application.port.inbound.job_run.list_job_runs.output import ListJobRunsOutput


class ListJobRunsUseCase(UseCase[ListJobRunsInput, ListJobRunsOutput]):
    """List all JobRuns associated with a Job."""
