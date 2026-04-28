"""UpdateTableProperties use case definition."""

from application.port.inbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesInput,
)
from application.port.inbound.catalog.update_table_properties.output import (
    UpdateTablePropertiesOutput,
)
from application.port.inbound.catalog.update_table_properties.use_case import (
    UpdateTablePropertiesUseCase,
)

__all__ = [
    "UpdateTablePropertiesInput",
    "UpdateTablePropertiesOutput",
    "UpdateTablePropertiesUseCase",
]
