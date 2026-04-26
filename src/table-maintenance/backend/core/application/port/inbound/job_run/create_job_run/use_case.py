"""Define the CreateJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from core.application.port.inbound.job_run.create_job_run.input import CreateJobRunInput
from core.application.port.inbound.job_run.create_job_run.output import (
    TriggerJobOutput,
)


class CreateJobRunUseCase(UseCase[CreateJobRunInput, TriggerJobOutput]):
    """Trigger a new execution of a Job — returns acceptance, not run details."""
