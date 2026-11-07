"""Set and remove properties of an Iceberg table, guarded by the uuid that was loaded."""

from context.catalog.application.port.inbound.table.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.table.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)
from context.catalog.application.port.inbound.table.update_table_properties.use_case import (
    UpdateTablePropertiesUseCase,
)

__all__ = [
    "UpdateTablePropertiesUseCase",
    "UpdateTablePropertiesUseCaseInput",
    "UpdateTablePropertiesUseCaseOutput",
]
