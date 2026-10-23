"""Define the GetManagedTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.get_managed_table.input import (
    GetManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.get_managed_table.output import (
    GetManagedTableUseCaseOutput,
)
from base.use_case import UseCase


class GetManagedTableUseCase(
    UseCase[GetManagedTableUseCaseInput, GetManagedTableUseCaseOutput]
):
    """Get one managed table."""

    @abstractmethod
    def execute(
        self, request: GetManagedTableUseCaseInput
    ) -> GetManagedTableUseCaseOutput:
        """Get one managed table."""
