"""Define the ListTablePropertiesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.list_table_properties.input import (
    ListTablePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.table.list_table_properties.output import (
    ListTablePropertiesUseCaseOutput,
)


class ListTablePropertiesUseCase(UseCase[ListTablePropertiesUseCaseInput, ListTablePropertiesUseCaseOutput]):
    """List every property of an Iceberg table next to its default."""

    @abstractmethod
    def execute(self, request: ListTablePropertiesUseCaseInput) -> ListTablePropertiesUseCaseOutput:
        """List every property of an Iceberg table next to its default."""
