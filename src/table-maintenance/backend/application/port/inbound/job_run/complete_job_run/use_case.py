"""Define the CompleteJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.complete_job_run.input import CompleteJobRunInput
from application.port.inbound.job_run.complete_job_run.output import (
    CompleteJobRunOutput,
)


class CompleteJobRunUseCase(UseCase[CompleteJobRunInput, CompleteJobRunOutput]):
    """Mark a job run as completed with result metadata."""
