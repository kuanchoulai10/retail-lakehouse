"""Catalog gateway port."""

from application.port.outbound.catalog.read_catalog import ReadCatalogGateway
from application.port.outbound.catalog.update_table_properties import (
    UpdateTablePropertiesGateway,
    UpdateTablePropertiesInput,
)

__all__ = [
    "ReadCatalogGateway",
    "UpdateTablePropertiesGateway",
    "UpdateTablePropertiesInput",
]
