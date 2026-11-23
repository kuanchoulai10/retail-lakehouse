"""Define the TableDiscoveryPolicyAttachment aggregate root."""

from __future__ import annotations

from datetime import datetime

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    TableDiscoveryPolicyAttachmentId,
    TableDiscoveryPolicyId,
)


class TableDiscoveryPolicyAttachment(AggregateRoot[TableDiscoveryPolicyAttachmentId]):
    """The discovery policy attached to one catalog, namespace or table, pointed at by its id.

    A target holds at most one discovery attachment; the nearest one on a table's walk decides it.
    """

    id: TableDiscoveryPolicyAttachmentId
    target: PolicyTarget
    policy_id: TableDiscoveryPolicyId
    attached_at: datetime

    @classmethod
    def attach(
        cls,
        target: PolicyTarget,
        policy_id: TableDiscoveryPolicyId,
        now: datetime,
    ) -> TableDiscoveryPolicyAttachment:
        """Attach a policy to a target, under a new ``da-`` id."""
        return cls(id=TableDiscoveryPolicyAttachmentId.new(), target=target, policy_id=policy_id, attached_at=now)

    def replace_policy(self, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        """Attach another policy to the same target, keeping this attachment's id."""
        self._assign_together(policy_id=policy_id, attached_at=now)

    @property
    def catalog(self) -> str:
        """Return the catalog the target is in: the first element of its path.

        An Iceberg table cannot leave its catalog, so a table attachment's catalog never goes stale.
        """
        return self.target.path[0]
