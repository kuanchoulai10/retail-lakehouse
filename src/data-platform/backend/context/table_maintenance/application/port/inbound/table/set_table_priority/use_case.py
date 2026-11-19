"""Define the SetTablePriorityUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.set_table_priority.input import (
    SetTablePriorityUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.set_table_priority.output import (
    SetTablePriorityUseCaseOutput,
)


class SetTablePriorityUseCase(UseCase[SetTablePriorityUseCaseInput, SetTablePriorityUseCaseOutput]):
    """Set how urgently a table's maintenance is scheduled."""

    @abstractmethod
    def execute(self, request: SetTablePriorityUseCaseInput) -> SetTablePriorityUseCaseOutput:
        """Set how urgently a table's maintenance is scheduled."""
