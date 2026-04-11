from __future__ import annotations

from base.use_case import UseCase

from jobs.application.port.inbound.delete_job.input import DeleteJobInput
from jobs.application.port.inbound.delete_job.output import DeleteJobOutput


class DeleteJobUseCase(UseCase[DeleteJobInput, DeleteJobOutput]):
    """Delete a table maintenance job by its ID."""
