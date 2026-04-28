"""Define the UpdateJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.update_job.input import UpdateJobUseCaseInput
from application.port.inbound.job.update_job.output import UpdateJobUseCaseOutput


class UpdateJobUseCase(UseCase[UpdateJobUseCaseInput, UpdateJobUseCaseOutput]):
    """Partially update an existing Job definition."""
