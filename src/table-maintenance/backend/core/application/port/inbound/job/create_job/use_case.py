"""Define the CreateJobUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from core.application.port.inbound.job.create_job.input import CreateJobInput
from core.application.port.inbound.job.create_job.output import CreateJobOutput


class CreateJobUseCase(UseCase[CreateJobInput, CreateJobOutput]):
    """Create a new table maintenance job."""
