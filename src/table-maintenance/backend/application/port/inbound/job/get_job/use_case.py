"""Define the GetJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.get_job.input import GetJobUseCaseInput
from application.port.inbound.job.get_job.output import GetJobUseCaseOutput


class GetJobUseCase(UseCase[GetJobUseCaseInput, GetJobUseCaseOutput]):
    """Retrieve a single job by its ID."""
