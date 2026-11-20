"""Compare one schema version of an Iceberg table with another, matching fields by field id."""

from context.catalog.application.port.inbound.table.get_table_schema_comparison.input import (
    GetTableSchemaComparisonUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table_schema_comparison.output import (
    GetTableSchemaComparisonUseCaseOutput,
)
from context.catalog.application.port.inbound.table.get_table_schema_comparison.use_case import (
    GetTableSchemaComparisonUseCase,
)

__all__ = [
    "GetTableSchemaComparisonUseCase",
    "GetTableSchemaComparisonUseCaseInput",
    "GetTableSchemaComparisonUseCaseOutput",
]
