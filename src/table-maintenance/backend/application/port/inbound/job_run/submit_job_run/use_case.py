"""Define the SubmitJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job_run.submit_job_run.input import (
    SubmitJobRunUseCaseInput,
)


class SubmitJobRunUseCase(UseCase[SubmitJobRunUseCaseInput, None]):
    """Submit a job run to an external execution system."""
