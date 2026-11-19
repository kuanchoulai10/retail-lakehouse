"""Define the InMemoryTableMaintenancePolicyAttachmentsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicyName,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
        PolicyTarget,
        TableMaintenancePolicyAttachment,
    )


class InMemoryTableMaintenancePolicyAttachmentsRepo(TableMaintenancePolicyAttachmentsRepo):
    """Keep attachments in a dict keyed by attachment id, and refuse what the SQL repo refuses.

    Like the SQL primary key and the unique ``target_key`` index, a new attachment may reuse
    neither a stored id nor a target that already has an attachment.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMaintenancePolicyAttachment] = {}

    def create(self, entity: TableMaintenancePolicyAttachment) -> TableMaintenancePolicyAttachment:
        """Insert an attachment; a second one on the same target raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"attachment id already stored: {entity.id.value!r}")
        if self.get_by_target(entity.target) is not None:
            raise ConflictError(f"target already has an attachment: {entity.target.key()!r}")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePolicyAttachment | None:
        """Return the attachment or None."""
        return self.items.get(entity_id.value)

    def get_by_target(self, target: PolicyTarget) -> TableMaintenancePolicyAttachment | None:
        """Return the attachment on the target, matched by its key, or None."""
        return next((a for a in self.items.values() if a.target.key() == target.key()), None)

    def get_many_by_targets(self, targets: Sequence[PolicyTarget]) -> list[TableMaintenancePolicyAttachment]:
        """Return the stored attachments on any of ``targets``, matched by key."""
        keys = {t.key() for t in targets}
        return [a for a in self.items.values() if a.target.key() in keys]

    def list_all(self) -> list[TableMaintenancePolicyAttachment]:
        """Return attachments ordered by id."""
        return [self.items[key] for key in sorted(self.items)]

    def update(self, attachment: TableMaintenancePolicyAttachment) -> TableMaintenancePolicyAttachment:
        """Replace a stored attachment."""
        if attachment.id.value not in self.items:
            raise LookupError(f"attachment {attachment.id.value} does not exist")
        self.items[attachment.id.value] = attachment
        return attachment

    def delete(self, entity_id: EntityId) -> None:
        """Remove an attachment if present."""
        self.items.pop(entity_id.value, None)

    def get_many(self, ids: Sequence[EntityId]) -> list[TableMaintenancePolicyAttachment]:
        """Return the stored attachments among ``ids``."""
        return [self.items[i.value] for i in ids if i.value in self.items]

    def list_for_policy(self, policy_name: TableMaintenancePolicyName) -> list[TableMaintenancePolicyAttachment]:
        """Return the attachments of one policy, ordered by id."""
        return [a for a in self.list_all() if a.policy_name == policy_name]

    def has_attachments_for_policy(self, policy_name: TableMaintenancePolicyName) -> bool:
        """Return whether any attachment uses the policy."""
        return any(a.policy_name == policy_name for a in self.items.values())
