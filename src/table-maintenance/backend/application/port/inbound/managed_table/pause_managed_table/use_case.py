"""Define the PauseManagedTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.pause_managed_table.input import (
    PauseManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.pause_managed_table.output import (
    PauseManagedTableUseCaseOutput,
)
from base.use_case import UseCase


class PauseManagedTableUseCase(
    UseCase[PauseManagedTableUseCaseInput, PauseManagedTableUseCaseOutput]
):
    """Pause maintenance of a managed table."""

    @abstractmethod
    def execute(
        self, request: PauseManagedTableUseCaseInput
    ) -> PauseManagedTableUseCaseOutput:
        """Pause maintenance of a managed table."""
