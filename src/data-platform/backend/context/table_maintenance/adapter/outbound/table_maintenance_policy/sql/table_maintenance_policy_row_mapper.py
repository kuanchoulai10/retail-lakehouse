"""Define the TableMaintenancePolicyRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
    TableMaintenancePolicyVersion,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableMaintenancePolicyRowMapper:
    """Convert between TableMaintenancePolicy aggregates and table rows."""

    @staticmethod
    def to_policy_values(policy: TableMaintenancePolicy) -> dict[str, Any]:
        """Return the columns of the policy row."""
        return {
            "name": policy.id.value,
            "version": policy.version,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }

    @staticmethod
    def to_version_values(version: TableMaintenancePolicyVersion) -> dict[str, Any]:
        """Return the columns of a version row."""
        return {
            "name": version.name.value,
            "version": version.version,
            "content_json": version.content.to_primitives(),
            "created_at": version.created_at,
        }

    @staticmethod
    def to_aggregate(policy_row: RowMapping, version_row: RowMapping) -> TableMaintenancePolicy:
        """Rebuild the aggregate from its policy row and its current version row."""
        return TableMaintenancePolicy(
            id=TableMaintenancePolicyName(policy_row["name"]),
            content=MaintenancePolicyContent.from_primitives(version_row["content_json"]),
            version=policy_row["version"],
            created_at=policy_row["created_at"],
            updated_at=policy_row["updated_at"],
        )

    @staticmethod
    def to_version(row: RowMapping) -> TableMaintenancePolicyVersion:
        """Rebuild a version record from a version row."""
        return TableMaintenancePolicyVersion(
            name=TableMaintenancePolicyName(row["name"]),
            version=row["version"],
            content=MaintenancePolicyContent.from_primitives(row["content_json"]),
            created_at=row["created_at"],
        )
