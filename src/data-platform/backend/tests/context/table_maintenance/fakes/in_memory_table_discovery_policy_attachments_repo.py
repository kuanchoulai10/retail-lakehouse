"""Define the InMemoryTableDiscoveryPolicyAttachmentsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.shared import PolicyTarget
    from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyId


class InMemoryTableDiscoveryPolicyAttachmentsRepo(TableDiscoveryPolicyAttachmentsRepo):
    """Keep attachments in a dict keyed by attachment id, and refuse what the SQL repo refuses.

    Like the SQL primary key and the unique ``target_key`` index, a new attachment may reuse
    neither a stored id nor a target that already has an attachment. Each read returns a copy,
    so a change reaches the store only through ``update``.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableDiscoveryPolicyAttachment] = {}

    def create(self, entity: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
        """Insert an attachment; a second one on the same target raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"discovery attachment id already stored: {entity.id.value!r}")
        if self.get_by_target(entity.target) is not None:
            raise ConflictError(f"target already has a discovery attachment: {entity.target.key()!r}")
        self.items[entity.id.value] = _copy(entity)
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryPolicyAttachment | None:
        """Return a copy of the attachment or None."""
        found = self.items.get(entity_id.value)
        return None if found is None else _copy(found)

    def get_by_target(self, target: PolicyTarget) -> TableDiscoveryPolicyAttachment | None:
        """Return the attachment on the target, matched by its key, or None."""
        return next((a for a in self.list_all() if a.target.key() == target.key()), None)

    def get_many_by_targets(self, targets: Sequence[PolicyTarget]) -> list[TableDiscoveryPolicyAttachment]:
        """Return the stored attachments on any of ``targets``, matched by key."""
        keys = {t.key() for t in targets}
        return [a for a in self.list_all() if a.target.key() in keys]

    def list_in_catalog(self, catalog: str) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments whose target is in ``catalog``, ordered by id."""
        return [a for a in self.list_all() if a.catalog == catalog]

    def list_all(self) -> list[TableDiscoveryPolicyAttachment]:
        """Return copies of the attachments ordered by id."""
        return [_copy(self.items[key]) for key in sorted(self.items)]

    def list_for_policy(self, policy_id: TableDiscoveryPolicyId) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments of one policy, ordered by id."""
        return [a for a in self.list_all() if a.policy_id == policy_id]

    def has_attachments_for_policy(self, policy_id: TableDiscoveryPolicyId) -> bool:
        """Return whether any attachment uses the policy."""
        return any(a.policy_id == policy_id for a in self.items.values())

    def update(self, attachment: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
        """Replace a stored attachment."""
        if attachment.id.value not in self.items:
            raise LookupError(f"discovery attachment {attachment.id.value} does not exist")
        self.items[attachment.id.value] = _copy(attachment)
        return attachment

    def delete(self, entity_id: EntityId) -> None:
        """Remove an attachment if present."""
        self.items.pop(entity_id.value, None)


def _copy(attachment: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
    return TableDiscoveryPolicyAttachment(
        id=attachment.id, target=attachment.target, policy_id=attachment.policy_id, attached_at=attachment.attached_at
    )
