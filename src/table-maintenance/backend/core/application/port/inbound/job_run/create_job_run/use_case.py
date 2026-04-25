"""Define the CreateJobRunUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from core.application.port.inbound.job_run.create_job_run.input import CreateJobRunInput
from core.application.port.inbound.job_run.create_job_run.output import (
    CreateJobRunOutput,
)


class CreateJobRunUseCase(UseCase[CreateJobRunInput, CreateJobRunOutput]):
    """Trigger a new execution of a Job, producing a JobRun."""
