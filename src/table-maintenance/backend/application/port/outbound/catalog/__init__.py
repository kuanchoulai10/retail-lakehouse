"""Catalog gateway port."""

from application.port.outbound.catalog.read_catalog import ReadCatalogGateway
from application.port.outbound.catalog.update_table_properties import (
    UpdateTablePropertiesGateway,
    UpdateTablePropertiesGatewayInput,
)

__all__ = [
    "ReadCatalogGateway",
    "UpdateTablePropertiesGateway",
    "UpdateTablePropertiesGatewayInput",
]
