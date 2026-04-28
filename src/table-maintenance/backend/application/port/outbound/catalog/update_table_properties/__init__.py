"""UpdateTableProperties gateway port."""

from application.port.outbound.catalog.update_table_properties.gateway import (
    UpdateTablePropertiesGateway,
)
from application.port.outbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesGatewayInput,
)

__all__ = ["UpdateTablePropertiesGateway", "UpdateTablePropertiesGatewayInput"]
