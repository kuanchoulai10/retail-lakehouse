"""Define the InMemoryTableMaintenancePoliciesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableMaintenancePolicyId
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePoliciesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicy,
        TableMaintenancePolicyName,
        TableMaintenancePolicyVersion,
    )
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore


class InMemoryTableMaintenancePoliciesRepo(TableMaintenancePoliciesRepo):
    """Keep policies by id and their versions in dicts, refusing what the SQL repo refuses.

    Ids and names are unique. Given ``placements``, a delete of a policy a catalog, namespace or table
    holds is refused, as the SQL foreign keys refuse it. Link ``placements`` only in repo contract
    tests: a service test builds the fake unlinked, so a service that forgets its own attached check
    deletes the policy and the test fails.
    """

    def __init__(self, *, placements: PolicyPlacementsStore | None = None) -> None:
        """Start empty, optionally reading the placements a delete must not orphan."""
        self.items: dict[str, TableMaintenancePolicy] = {}
        self.versions: dict[tuple[str, int], TableMaintenancePolicyVersion] = {}
        self._placements = placements

    def create(self, entity: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Insert a policy and its first version; a taken id or name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"policy id {entity.id.value!r} exists")
        if self.get_by_name(entity.name) is not None:
            raise ConflictError(f"policy name {entity.name.value!r} exists")
        self.items[entity.id.value] = entity
        self._record(entity)
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePolicy | None:
        """Return the policy or None."""
        return self.items.get(entity_id.value)

    def get_by_name(self, name: TableMaintenancePolicyName) -> TableMaintenancePolicy | None:
        """Return the policy with the name or None."""
        return next((p for p in self.items.values() if p.name == name), None)

    def get_many(self, ids: Sequence[EntityId]) -> list[TableMaintenancePolicy]:
        """Return the stored policies among ``ids``."""
        return [self.items[i.value] for i in ids if i.value in self.items]

    def list_all(self) -> list[TableMaintenancePolicy]:
        """Return policies ordered by name."""
        return sorted(self.items.values(), key=lambda p: p.name.value)

    def update(self, policy: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Replace a stored policy and record its new version."""
        if policy.id.value not in self.items:
            raise LookupError(f"table maintenance policy {policy.id.value} does not exist")
        self.items[policy.id.value] = policy
        self._record(policy)
        return policy

    def get_version(self, policy_id: EntityId, version: int) -> TableMaintenancePolicyVersion | None:
        """Return one stored version or None."""
        return self.versions.get((policy_id.value, version))

    def delete(self, entity_id: EntityId) -> None:
        """Remove a policy and its versions if present; one still attached raises ConflictError and stays."""
        if self._placements is not None and self._placements.maintenance_placements(
            TableMaintenancePolicyId(entity_id.value)
        ):
            raise ConflictError(f"policy {entity_id.value} is still attached to a catalog, namespace or table")
        self.items.pop(entity_id.value, None)
        for key in [k for k in self.versions if k[0] == entity_id.value]:
            del self.versions[key]

    def _record(self, policy: TableMaintenancePolicy) -> None:
        self.versions[(policy.id.value, policy.version)] = policy.current_version()
