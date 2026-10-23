"""Define the ReadCatalogGatewayTableRef."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadCatalogGatewayTableRef:
    """Locate a table by catalog, dot-joined namespace and table name."""

    catalog: str
    namespace: str
    table: str
