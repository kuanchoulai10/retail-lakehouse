"""Define the NamespaceRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.namespace import (
    Namespace,
    NamespaceId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class NamespaceRowMapper:
    """Map a Namespace to its row and back.

    The id column is the namespace id itself; the catalog and the levels are kept beside it, the
    catalog for listing a catalog's namespaces and the levels as a JSON list. A policy column is
    NULL when no policy of its kind is attached.
    """

    @staticmethod
    def to_values(namespace: Namespace) -> dict[str, Any]:
        """Return the column values of the namespace's row."""
        return {
            "id": namespace.id.value,
            "catalog": namespace.catalog,
            "path_json": list(namespace.levels),
            "discovery_policy_id": (
                None if namespace.discovery_policy_id is None else namespace.discovery_policy_id.value
            ),
            "maintenance_policy_id": (
                None if namespace.maintenance_policy_id is None else namespace.maintenance_policy_id.value
            ),
            "version": namespace.version,
            "created_at": namespace.created_at,
            "updated_at": namespace.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> Namespace:
        """Rebuild the namespace from its row without registering events."""
        discovery = row["discovery_policy_id"]
        maintenance = row["maintenance_policy_id"]
        return Namespace(
            id=NamespaceId.of(row["catalog"], tuple(row["path_json"])),
            discovery_policy_id=None if discovery is None else TableDiscoveryPolicyId(discovery),
            maintenance_policy_id=None if maintenance is None else TableMaintenancePolicyId(maintenance),
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
