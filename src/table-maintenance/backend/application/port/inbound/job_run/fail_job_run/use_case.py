"""Define the FailJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.fail_job_run.input import FailJobRunUseCaseInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunUseCaseOutput


class FailJobRunUseCase(UseCase[FailJobRunUseCaseInput, FailJobRunUseCaseOutput]):
    """Mark a job run as failed with error details."""
