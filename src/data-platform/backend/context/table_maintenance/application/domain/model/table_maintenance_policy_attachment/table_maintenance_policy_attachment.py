"""Define the TableMaintenancePolicyAttachment aggregate root."""

from __future__ import annotations

from datetime import datetime

from base import AggregateRoot
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment.policy_target import (
    PolicyTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment.table_maintenance_policy_attachment_id import (  # noqa: E501
    TableMaintenancePolicyAttachmentId,
)


class TableMaintenancePolicyAttachment(AggregateRoot[TableMaintenancePolicyAttachmentId]):
    """The maintenance policy attached to one catalog, namespace or table."""

    id: TableMaintenancePolicyAttachmentId
    target: PolicyTarget
    policy_name: TableMaintenancePolicyName
    attached_at: datetime

    @classmethod
    def attach(
        cls,
        target: PolicyTarget,
        policy_name: TableMaintenancePolicyName,
        now: datetime,
    ) -> TableMaintenancePolicyAttachment:
        """Attach a policy to a target, under a new ``pa-`` id."""
        return cls(id=TableMaintenancePolicyAttachmentId.new(), target=target, policy_name=policy_name, attached_at=now)

    def replace_policy(self, policy_name: TableMaintenancePolicyName, now: datetime) -> None:
        """Attach another policy to the same target."""
        self._assign_together(policy_name=policy_name, attached_at=now)
