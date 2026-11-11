"""Define the InMemoryTableMaintenancePoliciesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePoliciesRepo,
)

if TYPE_CHECKING:
    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicy,
        TableMaintenancePolicyName,
        TableMaintenancePolicyVersion,
    )


class InMemoryTableMaintenancePoliciesRepo(TableMaintenancePoliciesRepo):
    """Keep policies and their versions in dicts, enforcing unique names like the SQL repo."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMaintenancePolicy] = {}
        self.versions: dict[tuple[str, int], TableMaintenancePolicyVersion] = {}

    def create(self, entity: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Insert a policy and its first version; a duplicate name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"policy name {entity.id.value!r} exists")
        self.items[entity.id.value] = entity
        self._record(entity)
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePolicy | None:
        """Return the policy or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableMaintenancePolicy]:
        """Return policies ordered by name."""
        return sorted(self.items.values(), key=lambda p: p.id.value)

    def update(self, policy: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Replace a stored policy and record its new version."""
        if policy.id.value not in self.items:
            raise LookupError(f"table maintenance policy {policy.id.value} does not exist")
        self.items[policy.id.value] = policy
        self._record(policy)
        return policy

    def get_version(self, name: TableMaintenancePolicyName, version: int) -> TableMaintenancePolicyVersion | None:
        """Return one stored version or None."""
        return self.versions.get((name.value, version))

    def delete(self, entity_id: EntityId) -> None:
        """Remove a policy and its versions if present."""
        self.items.pop(entity_id.value, None)
        for key in [k for k in self.versions if k[0] == entity_id.value]:
            del self.versions[key]

    def _record(self, policy: TableMaintenancePolicy) -> None:
        self.versions[(policy.id.value, policy.version)] = policy.current_version()
