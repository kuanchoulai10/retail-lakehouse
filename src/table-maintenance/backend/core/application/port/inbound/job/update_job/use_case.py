"""Define the UpdateJobUseCase interface."""

from __future__ import annotations

from core.base.use_case import UseCase

from core.application.port.inbound.job.update_job.input import UpdateJobInput
from core.application.port.inbound.job.update_job.output import UpdateJobOutput


class UpdateJobUseCase(UseCase[UpdateJobInput, UpdateJobOutput]):
    """Partially update an existing Job definition."""
