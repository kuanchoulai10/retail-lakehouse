"""Define the CatalogRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.catalog import (
    Catalog,
    CatalogId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class CatalogRowMapper:
    """Map a Catalog to its row and back; a policy column is NULL when no policy of its kind is attached."""

    @staticmethod
    def to_values(catalog: Catalog) -> dict[str, Any]:
        """Return the column values of the catalog's row."""
        return {
            "name": catalog.id.value,
            "discovery_policy_id": None if catalog.discovery_policy_id is None else catalog.discovery_policy_id.value,
            "maintenance_policy_id": (
                None if catalog.maintenance_policy_id is None else catalog.maintenance_policy_id.value
            ),
            "version": catalog.version,
            "created_at": catalog.created_at,
            "updated_at": catalog.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> Catalog:
        """Rebuild the catalog from its row without registering events."""
        discovery = row["discovery_policy_id"]
        maintenance = row["maintenance_policy_id"]
        return Catalog(
            id=CatalogId(row["name"]),
            discovery_policy_id=None if discovery is None else TableDiscoveryPolicyId(discovery),
            maintenance_policy_id=None if maintenance is None else TableMaintenancePolicyId(maintenance),
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
