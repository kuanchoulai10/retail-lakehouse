from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.get_job.input import GetJobInput
from application.port.inbound.get_job.output import GetJobOutput


class GetJobUseCase(UseCase[GetJobInput, GetJobOutput]):
    """Retrieve a single job by its ID."""
