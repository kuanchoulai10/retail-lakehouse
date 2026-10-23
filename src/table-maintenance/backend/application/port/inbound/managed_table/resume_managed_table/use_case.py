"""Define the ResumeManagedTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.resume_managed_table.input import (
    ResumeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.resume_managed_table.output import (
    ResumeManagedTableUseCaseOutput,
)
from base.use_case import UseCase


class ResumeManagedTableUseCase(
    UseCase[ResumeManagedTableUseCaseInput, ResumeManagedTableUseCaseOutput]
):
    """Resume maintenance of a managed table."""

    @abstractmethod
    def execute(
        self, request: ResumeManagedTableUseCaseInput
    ) -> ResumeManagedTableUseCaseOutput:
        """Resume maintenance of a managed table."""
