"""Define the TableDiscoveryPolicyAttachmentRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyAttachment,
    TableDiscoveryPolicyAttachmentId,
    TableDiscoveryPolicyId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableDiscoveryPolicyAttachmentRowMapper:
    """Convert between TableDiscoveryPolicyAttachment aggregates and table rows."""

    @staticmethod
    def to_values(attachment: TableDiscoveryPolicyAttachment) -> dict[str, Any]:
        """Return the columns of the attachment row.

        ``target_key`` is the target's unique key, and ``catalog`` the catalog the target is in,
        so a scan reads only its own catalog's attachments.
        """
        return {
            "id": attachment.id.value,
            "target_key": attachment.target.key(),
            "target_type": attachment.target.type.value,
            "path_json": list(attachment.target.path),
            "table_uuid": attachment.target.table_uuid,
            "catalog": attachment.catalog,
            "policy_id": attachment.policy_id.value,
            "attached_at": attachment.attached_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableDiscoveryPolicyAttachment:
        """Rebuild the aggregate from its row; the catalog is read from the path, not the column."""
        return TableDiscoveryPolicyAttachment(
            id=TableDiscoveryPolicyAttachmentId(row["id"]),
            target=PolicyTarget(
                type=PolicyTargetType(row["target_type"]),
                path=tuple(row["path_json"]),
                table_uuid=row["table_uuid"],
            ),
            policy_id=TableDiscoveryPolicyId(row["policy_id"]),
            attached_at=row["attached_at"],
        )
