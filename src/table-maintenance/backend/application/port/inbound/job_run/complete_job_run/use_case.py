"""Define the CompleteJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.complete_job_run.input import (
    CompleteJobRunUseCaseInput,
)
from application.port.inbound.job_run.complete_job_run.output import (
    CompleteJobRunUseCaseOutput,
)


class CompleteJobRunUseCase(
    UseCase[CompleteJobRunUseCaseInput, CompleteJobRunUseCaseOutput]
):
    """Mark a job run as completed with result metadata."""
