"""Define the TableMaintenancePolicyAttachmentRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyAttachment,
    TableMaintenancePolicyAttachmentId,
    TableMaintenancePolicyName,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableMaintenancePolicyAttachmentRowMapper:
    """Convert between TableMaintenancePolicyAttachment aggregates and table rows."""

    @staticmethod
    def to_values(attachment: TableMaintenancePolicyAttachment) -> dict[str, Any]:
        """Return the columns of the attachment row."""
        return {
            "id": attachment.id.value,
            "target_type": attachment.target.type.value,
            "path_json": list(attachment.target.path),
            "table_uuid": attachment.target.table_uuid,
            "policy_name": attachment.policy_name.value,
            "attached_at": attachment.attached_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableMaintenancePolicyAttachment:
        """Rebuild the aggregate from its row."""
        return TableMaintenancePolicyAttachment(
            id=TableMaintenancePolicyAttachmentId(row["id"]),
            target=PolicyTarget(
                type=PolicyTargetType(row["target_type"]),
                path=tuple(row["path_json"]),
                table_uuid=row["table_uuid"],
            ),
            policy_name=TableMaintenancePolicyName(row["policy_name"]),
            attached_at=row["attached_at"],
        )
