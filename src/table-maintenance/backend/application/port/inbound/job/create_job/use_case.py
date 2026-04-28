"""Define the CreateJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.create_job.input import CreateJobUseCaseInput
from application.port.inbound.job.create_job.output import CreateJobUseCaseOutput


class CreateJobUseCase(UseCase[CreateJobUseCaseInput, CreateJobUseCaseOutput]):
    """Create a new table maintenance job."""
