"""Read tables and their statistics from the catalog."""

from application.port.outbound.catalog.read_catalog.gateway import ReadCatalogGateway
from application.port.outbound.catalog.read_catalog.list_input import (
    ReadCatalogGatewayListInput,
)
from application.port.outbound.catalog.read_catalog.observation import (
    ReadCatalogGatewayObservation,
)
from application.port.outbound.catalog.read_catalog.table import ReadCatalogGatewayTable
from application.port.outbound.catalog.read_catalog.table_ref import (
    ReadCatalogGatewayTableRef,
)

__all__ = [
    "ReadCatalogGateway",
    "ReadCatalogGatewayListInput",
    "ReadCatalogGatewayObservation",
    "ReadCatalogGatewayTable",
    "ReadCatalogGatewayTableRef",
]
