"""Define the GetGenericTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.generic_table.get_generic_table.input import (
    GetGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.output import (
    GetGenericTableUseCaseOutput,
)


class GetGenericTableUseCase(UseCase[GetGenericTableUseCaseInput, GetGenericTableUseCaseOutput]):
    """Get one generic table with its format, base location, doc and properties."""

    @abstractmethod
    def execute(self, request: GetGenericTableUseCaseInput) -> GetGenericTableUseCaseOutput:
        """Get one generic table with its format, base location, doc and properties."""
