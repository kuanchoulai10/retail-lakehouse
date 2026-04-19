"""Define the GetJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.get_job_run.input import GetJobRunInput
from application.port.inbound.job_run.get_job_run.output import GetJobRunOutput


class GetJobRunUseCase(UseCase[GetJobRunInput, GetJobRunOutput]):
    """Retrieve a specific JobRun by run_id."""
