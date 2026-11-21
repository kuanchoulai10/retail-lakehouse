"""Define the TableMaintenancePolicyAttachment aggregate root."""

from __future__ import annotations

from datetime import datetime

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import PolicyTarget
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment.table_maintenance_policy_attachment_id import (  # noqa: E501
    TableMaintenancePolicyAttachmentId,
)


class TableMaintenancePolicyAttachment(AggregateRoot[TableMaintenancePolicyAttachmentId]):
    """The maintenance policy attached to one catalog, namespace or table, pointed at by its id."""

    id: TableMaintenancePolicyAttachmentId
    target: PolicyTarget
    policy_id: TableMaintenancePolicyId
    attached_at: datetime

    @classmethod
    def attach(
        cls,
        target: PolicyTarget,
        policy_id: TableMaintenancePolicyId,
        now: datetime,
    ) -> TableMaintenancePolicyAttachment:
        """Attach a policy to a target, under a new ``pa-`` id."""
        return cls(id=TableMaintenancePolicyAttachmentId.new(), target=target, policy_id=policy_id, attached_at=now)

    def replace_policy(self, policy_id: TableMaintenancePolicyId, now: datetime) -> None:
        """Attach another policy to the same target."""
        self._assign_together(policy_id=policy_id, attached_at=now)
