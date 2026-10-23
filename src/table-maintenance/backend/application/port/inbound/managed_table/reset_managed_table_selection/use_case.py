"""Define the ResetManagedTableSelectionUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.reset_managed_table_selection.input import (
    ResetManagedTableSelectionUseCaseInput,
)
from application.port.inbound.managed_table.reset_managed_table_selection.output import (
    ResetManagedTableSelectionUseCaseOutput,
)
from base.use_case import UseCase


class ResetManagedTableSelectionUseCase(
    UseCase[
        ResetManagedTableSelectionUseCaseInput, ResetManagedTableSelectionUseCaseOutput
    ]
):
    """Hand a table back to discovery rules."""

    @abstractmethod
    def execute(
        self, request: ResetManagedTableSelectionUseCaseInput
    ) -> ResetManagedTableSelectionUseCaseOutput:
        """Hand a table back to discovery rules."""
