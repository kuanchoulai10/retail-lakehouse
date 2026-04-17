from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.list_job_runs.input import ListJobRunsInput
from application.port.inbound.job_run.list_job_runs.output import ListJobRunsOutput


class ListJobRunsUseCase(UseCase[ListJobRunsInput, ListJobRunsOutput]):
    """List all JobRuns associated with a Job."""
