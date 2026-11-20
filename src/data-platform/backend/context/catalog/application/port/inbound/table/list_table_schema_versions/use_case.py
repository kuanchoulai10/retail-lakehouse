"""Define the ListTableSchemaVersionsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.list_table_schema_versions.input import (
    ListTableSchemaVersionsUseCaseInput,
)
from context.catalog.application.port.inbound.table.list_table_schema_versions.output import (
    ListTableSchemaVersionsUseCaseOutput,
)


class ListTableSchemaVersionsUseCase(
    UseCase[ListTableSchemaVersionsUseCaseInput, ListTableSchemaVersionsUseCaseOutput]
):
    """List every schema version of an Iceberg table, newest id first, with what each changed."""

    @abstractmethod
    def execute(self, request: ListTableSchemaVersionsUseCaseInput) -> ListTableSchemaVersionsUseCaseOutput:
        """List every schema version of an Iceberg table, newest id first, with what each changed."""
