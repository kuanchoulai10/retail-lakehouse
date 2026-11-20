"""Define the GetTableSchemaComparisonUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.get_table_schema_comparison.input import (
    GetTableSchemaComparisonUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table_schema_comparison.output import (
    GetTableSchemaComparisonUseCaseOutput,
)


class GetTableSchemaComparisonUseCase(
    UseCase[GetTableSchemaComparisonUseCaseInput, GetTableSchemaComparisonUseCaseOutput]
):
    """Compare one schema version of an Iceberg table with another, matching fields by field id."""

    @abstractmethod
    def execute(self, request: GetTableSchemaComparisonUseCaseInput) -> GetTableSchemaComparisonUseCaseOutput:
        """Compare one schema version of an Iceberg table with another, matching fields by field id."""
