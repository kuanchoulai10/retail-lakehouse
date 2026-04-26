"""Define the GetJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from core.application.port.inbound.job.get_job.input import GetJobInput
from core.application.port.inbound.job.get_job.output import GetJobOutput


class GetJobUseCase(UseCase[GetJobInput, GetJobOutput]):
    """Retrieve a single job by its ID."""
