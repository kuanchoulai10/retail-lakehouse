"""Define the PauseTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.pause_table.input import (
    PauseTableUseCaseInput,
)
from application.port.inbound.table.pause_table.output import (
    PauseTableUseCaseOutput,
)
from base import UseCase


class PauseTableUseCase(UseCase[PauseTableUseCaseInput, PauseTableUseCaseOutput]):
    """Pause maintenance of a table."""

    @abstractmethod
    def execute(self, request: PauseTableUseCaseInput) -> PauseTableUseCaseOutput:
        """Pause maintenance of a table."""
