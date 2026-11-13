"""Define the CatalogDiscoveryRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class CatalogDiscoveryRowMapper:
    """Map a CatalogDiscovery to its row and back."""

    @staticmethod
    def to_values(discovery: CatalogDiscovery) -> dict[str, Any]:
        """Return the column values of the discovery's row."""
        return {"catalog": discovery.catalog, "last_discovered_at": discovery.last_discovered_at}

    @staticmethod
    def to_aggregate(row: RowMapping) -> CatalogDiscovery:
        """Rebuild the discovery from its row."""
        return CatalogDiscovery(id=CatalogDiscoveryId(row["catalog"]), last_discovered_at=row["last_discovered_at"])
