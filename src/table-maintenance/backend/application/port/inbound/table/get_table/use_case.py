"""Define the GetTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.get_table.input import (
    GetTableUseCaseInput,
)
from application.port.inbound.table.get_table.output import (
    GetTableUseCaseOutput,
)
from base.use_case import UseCase


class GetTableUseCase(UseCase[GetTableUseCaseInput, GetTableUseCaseOutput]):
    """Get one table."""

    @abstractmethod
    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Get one table."""
