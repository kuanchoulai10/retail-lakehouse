"""Define the DeleteJobUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.job.delete_job.input import DeleteJobUseCaseInput
from application.port.inbound.job.delete_job.output import DeleteJobUseCaseOutput


class DeleteJobUseCase(UseCase[DeleteJobUseCaseInput, DeleteJobUseCaseOutput]):
    """Delete a table maintenance job by its ID."""
