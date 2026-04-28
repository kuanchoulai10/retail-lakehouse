"""UpdateTableProperties gateway port."""

from application.port.outbound.catalog.update_table_properties.gateway import (
    UpdateTablePropertiesGateway,
)
from application.port.outbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesInput,
)

__all__ = ["UpdateTablePropertiesGateway", "UpdateTablePropertiesInput"]
