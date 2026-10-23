"""Define the ExcludeManagedTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.exclude_managed_table.input import (
    ExcludeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.exclude_managed_table.output import (
    ExcludeManagedTableUseCaseOutput,
)
from base.use_case import UseCase


class ExcludeManagedTableUseCase(
    UseCase[ExcludeManagedTableUseCaseInput, ExcludeManagedTableUseCaseOutput]
):
    """Exclude a table from maintenance by hand."""

    @abstractmethod
    def execute(
        self, request: ExcludeManagedTableUseCaseInput
    ) -> ExcludeManagedTableUseCaseOutput:
        """Exclude a table from maintenance by hand."""
