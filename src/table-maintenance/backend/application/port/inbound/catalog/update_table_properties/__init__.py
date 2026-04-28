"""UpdateTableProperties use case definition."""

from application.port.inbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from application.port.inbound.catalog.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)
from application.port.inbound.catalog.update_table_properties.use_case import (
    UpdateTablePropertiesUseCase,
)

__all__ = [
    "UpdateTablePropertiesUseCaseInput",
    "UpdateTablePropertiesUseCaseOutput",
    "UpdateTablePropertiesUseCase",
]
