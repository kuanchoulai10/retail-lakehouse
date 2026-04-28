"""Define the FailJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.fail_job_run.input import FailJobRunInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunOutput


class FailJobRunUseCase(UseCase[FailJobRunInput, FailJobRunOutput]):
    """Mark a job run as failed with error details."""
