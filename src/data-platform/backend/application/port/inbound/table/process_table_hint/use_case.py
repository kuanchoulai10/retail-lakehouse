"""Define the ProcessTableHintUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.process_table_hint.input import (
    ProcessTableHintUseCaseInput,
)
from application.port.inbound.table.process_table_hint.output import (
    ProcessTableHintUseCaseOutput,
)
from base import UseCase


class ProcessTableHintUseCase(
    UseCase[ProcessTableHintUseCaseInput, ProcessTableHintUseCaseOutput]
):
    """React to a catalog event hint about one table or namespace."""

    @abstractmethod
    def execute(
        self, request: ProcessTableHintUseCaseInput
    ) -> ProcessTableHintUseCaseOutput:
        """React to a catalog event hint about one table or namespace."""
