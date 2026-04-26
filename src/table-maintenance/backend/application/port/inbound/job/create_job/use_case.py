"""Define the CreateJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.create_job.input import CreateJobInput
from application.port.inbound.job.create_job.output import CreateJobOutput


class CreateJobUseCase(UseCase[CreateJobInput, CreateJobOutput]):
    """Create a new table maintenance job."""
