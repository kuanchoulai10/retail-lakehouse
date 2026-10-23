"""Define the ReadCatalogGatewayTable."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadCatalogGatewayTable:
    """A table located in the catalog, with its Iceberg table-uuid."""

    catalog: str
    namespace: str
    table: str
    table_uuid: str
