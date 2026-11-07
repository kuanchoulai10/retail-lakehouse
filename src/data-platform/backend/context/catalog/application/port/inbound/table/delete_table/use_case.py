"""Define the DeleteTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.delete_table.input import (
    DeleteTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.delete_table.output import (
    DeleteTableUseCaseOutput,
)


class DeleteTableUseCase(UseCase[DeleteTableUseCaseInput, DeleteTableUseCaseOutput]):
    """Drop an Iceberg table from the catalog without purging its files."""

    @abstractmethod
    def execute(self, request: DeleteTableUseCaseInput) -> DeleteTableUseCaseOutput:
        """Drop an Iceberg table from the catalog without purging its files."""
