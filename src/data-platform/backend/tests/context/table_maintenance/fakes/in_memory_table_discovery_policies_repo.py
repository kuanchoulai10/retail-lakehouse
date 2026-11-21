"""Define the InMemoryTableDiscoveryPoliciesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    TableDiscoveryPoliciesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        TableDiscoveryPolicyName,
        TableDiscoveryPolicyVersion,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class InMemoryTableDiscoveryPoliciesRepo(TableDiscoveryPoliciesRepo):
    """Keep policies by id and their versions in dicts, refusing what the SQL repo refuses.

    Each read returns a copy, so two readers hold independent copies and the second ``update``
    from the same version is stale, as in the database. Given ``attachments``, a delete of a policy
    attached there is refused, as the SQL foreign key refuses it.
    """

    def __init__(self, *, attachments: TableDiscoveryPolicyAttachmentsRepo | None = None) -> None:
        """Start empty, optionally sharing the attachments a delete must not orphan."""
        self.items: dict[str, TableDiscoveryPolicy] = {}
        self.versions: dict[tuple[str, int], TableDiscoveryPolicyVersion] = {}
        self._attachments = attachments

    def create(self, entity: TableDiscoveryPolicy) -> TableDiscoveryPolicy:
        """Insert a policy and its first version; a taken id or name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"discovery policy id {entity.id.value!r} exists")
        if self.get_by_name(entity.name) is not None:
            raise ConflictError(f"discovery policy name {entity.name.value!r} exists")
        self._store(entity)
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryPolicy | None:
        """Return a copy of the policy or None."""
        found = self.items.get(entity_id.value)
        return None if found is None else _copy(found)

    def get_by_name(self, name: TableDiscoveryPolicyName) -> TableDiscoveryPolicy | None:
        """Return a copy of the policy with the name or None."""
        return next((_copy(p) for p in self.items.values() if p.name == name), None)

    def get_many(self, ids: Sequence[EntityId]) -> list[TableDiscoveryPolicy]:
        """Return copies of the stored policies among ``ids``."""
        return [_copy(self.items[i.value]) for i in ids if i.value in self.items]

    def list_all(self) -> list[TableDiscoveryPolicy]:
        """Return copies of the policies ordered by name."""
        return [_copy(p) for p in sorted(self.items.values(), key=lambda p: p.name.value)]

    def update(self, policy: TableDiscoveryPolicy) -> TableDiscoveryPolicy:
        """Replace a stored policy and record its new version, when it was replaced from the stored version."""
        stored = self.items.get(policy.id.value)
        if stored is None:
            raise LookupError(f"table discovery policy {policy.id.value} does not exist")
        if stored.version != policy.version - 1:
            raise StaleDiscoveryPolicyVersion(f"discovery policy {policy.name.value} was changed concurrently")
        self._store(policy)
        return policy

    def get_version(self, policy_id: EntityId, version: int) -> TableDiscoveryPolicyVersion | None:
        """Return one stored version or None."""
        return self.versions.get((policy_id.value, version))

    def delete(self, entity_id: EntityId) -> None:
        """Remove a policy and its versions if present; one still attached raises ConflictError and stays."""
        if self._attachments is not None and self._attachments.has_attachments_for_policy(
            TableDiscoveryPolicyId(entity_id.value)
        ):
            raise ConflictError(f"discovery policy {entity_id.value} is still attached")
        self.items.pop(entity_id.value, None)
        for key in [k for k in self.versions if k[0] == entity_id.value]:
            del self.versions[key]

    def _store(self, policy: TableDiscoveryPolicy) -> None:
        self.items[policy.id.value] = _copy(policy)
        self.versions[(policy.id.value, policy.version)] = policy.current_version()


def _copy(policy: TableDiscoveryPolicy) -> TableDiscoveryPolicy:
    return TableDiscoveryPolicy(
        id=policy.id,
        name=policy.name,
        content=policy.content,
        version=policy.version,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )
