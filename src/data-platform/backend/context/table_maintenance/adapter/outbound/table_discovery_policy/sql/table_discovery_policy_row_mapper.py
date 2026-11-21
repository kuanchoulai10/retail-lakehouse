"""Define the TableDiscoveryPolicyRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyId,
    TableDiscoveryPolicyName,
    TableDiscoveryPolicyVersion,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableDiscoveryPolicyRowMapper:
    """Convert between TableDiscoveryPolicy aggregates and table rows."""

    @staticmethod
    def to_policy_values(policy: TableDiscoveryPolicy) -> dict[str, Any]:
        """Return the columns of the policy row."""
        return {
            "id": policy.id.value,
            "name": policy.name.value,
            "version": policy.version,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }

    @staticmethod
    def to_version_values(version: TableDiscoveryPolicyVersion) -> dict[str, Any]:
        """Return the columns of a version row; the content is stored in its wire shape."""
        return {
            "policy_id": version.policy_id.value,
            "version": version.version,
            "content_json": version.content.to_primitives(),
            "created_at": version.created_at,
        }

    @staticmethod
    def to_aggregate(policy_row: RowMapping, version_row: RowMapping) -> TableDiscoveryPolicy:
        """Rebuild the aggregate from its policy row and its current version row."""
        return TableDiscoveryPolicy(
            id=TableDiscoveryPolicyId(policy_row["id"]),
            name=TableDiscoveryPolicyName(value=policy_row["name"]),
            content=DiscoveryPolicyContent.from_primitives(version_row["content_json"]),
            version=policy_row["version"],
            created_at=policy_row["created_at"],
            updated_at=policy_row["updated_at"],
        )

    @staticmethod
    def to_version(row: RowMapping) -> TableDiscoveryPolicyVersion:
        """Rebuild a version record from a version row."""
        return TableDiscoveryPolicyVersion(
            policy_id=TableDiscoveryPolicyId(row["policy_id"]),
            version=row["version"],
            content=DiscoveryPolicyContent.from_primitives(row["content_json"]),
            created_at=row["created_at"],
        )
