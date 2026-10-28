"""Define the ResetTableSelectionUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.reset_table_selection.input import (
    ResetTableSelectionUseCaseInput,
)
from application.port.inbound.table.reset_table_selection.output import (
    ResetTableSelectionUseCaseOutput,
)
from base.use_case import UseCase


class ResetTableSelectionUseCase(
    UseCase[ResetTableSelectionUseCaseInput, ResetTableSelectionUseCaseOutput]
):
    """Hand a table back to discovery rules."""

    @abstractmethod
    def execute(
        self, request: ResetTableSelectionUseCaseInput
    ) -> ResetTableSelectionUseCaseOutput:
        """Hand a table back to discovery rules."""
