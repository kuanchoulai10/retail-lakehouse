"""Define the ResetTableSelectionUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.reset_table_selection.input import (
    ResetTableSelectionUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.reset_table_selection.output import (
    ResetTableSelectionUseCaseOutput,
)
from base import UseCase


class ResetTableSelectionUseCase(UseCase[ResetTableSelectionUseCaseInput, ResetTableSelectionUseCaseOutput]):
    """Hand a table back to discovery rules."""

    @abstractmethod
    def execute(self, request: ResetTableSelectionUseCaseInput) -> ResetTableSelectionUseCaseOutput:
        """Hand a table back to discovery rules."""
