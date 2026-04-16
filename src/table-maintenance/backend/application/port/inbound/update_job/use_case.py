from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.update_job.input import UpdateJobInput
from application.port.inbound.update_job.output import UpdateJobOutput


class UpdateJobUseCase(UseCase[UpdateJobInput, UpdateJobOutput]):
    """Partially update an existing Job definition."""
