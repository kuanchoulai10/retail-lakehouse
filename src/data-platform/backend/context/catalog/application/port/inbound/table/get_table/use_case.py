"""Define the GetTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.get_table.input import (
    GetTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table.output import (
    GetTableUseCaseOutput,
)


class GetTableUseCase(UseCase[GetTableUseCaseInput, GetTableUseCaseOutput]):
    """Get one Iceberg table with its schema, partition spec, sort order, snapshots and properties."""

    @abstractmethod
    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Get one Iceberg table with its schema, partition spec, sort order, snapshots and properties."""
