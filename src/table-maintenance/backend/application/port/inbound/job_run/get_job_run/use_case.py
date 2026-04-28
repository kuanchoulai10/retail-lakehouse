"""Define the GetJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.get_job_run.input import GetJobRunUseCaseInput
from application.port.inbound.job_run.get_job_run.output import GetJobRunUseCaseOutput


class GetJobRunUseCase(UseCase[GetJobRunUseCaseInput, GetJobRunUseCaseOutput]):
    """Retrieve a specific JobRun by run_id."""
