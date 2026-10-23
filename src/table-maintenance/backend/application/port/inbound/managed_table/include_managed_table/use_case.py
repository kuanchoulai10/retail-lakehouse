"""Define the IncludeManagedTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.include_managed_table.input import (
    IncludeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.include_managed_table.output import (
    IncludeManagedTableUseCaseOutput,
)
from base.use_case import UseCase


class IncludeManagedTableUseCase(
    UseCase[IncludeManagedTableUseCaseInput, IncludeManagedTableUseCaseOutput]
):
    """Include a table in maintenance by hand."""

    @abstractmethod
    def execute(
        self, request: IncludeManagedTableUseCaseInput
    ) -> IncludeManagedTableUseCaseOutput:
        """Include a table in maintenance by hand."""
