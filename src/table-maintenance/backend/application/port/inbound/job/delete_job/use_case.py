"""Define the DeleteJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.delete_job.input import DeleteJobInput
from application.port.inbound.job.delete_job.output import DeleteJobOutput


class DeleteJobUseCase(UseCase[DeleteJobInput, DeleteJobOutput]):
    """Delete a table maintenance job by its ID."""
