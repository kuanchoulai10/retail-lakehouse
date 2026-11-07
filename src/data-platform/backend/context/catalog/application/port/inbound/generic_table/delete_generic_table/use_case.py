"""Define the DeleteGenericTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.generic_table.delete_generic_table.input import (
    DeleteGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.output import (
    DeleteGenericTableUseCaseOutput,
)


class DeleteGenericTableUseCase(UseCase[DeleteGenericTableUseCaseInput, DeleteGenericTableUseCaseOutput]):
    """Drop a generic table from the catalog."""

    @abstractmethod
    def execute(self, request: DeleteGenericTableUseCaseInput) -> DeleteGenericTableUseCaseOutput:
        """Drop a generic table from the catalog."""
