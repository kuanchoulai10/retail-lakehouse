"""Define the Namespace aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    NamespaceId,
    PolicyNotAttached,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)


class Namespace(AggregateRoot[NamespaceId]):
    """Hold the discovery policy and the maintenance policy attached to one namespace, at most one of each.

    A policy attached here applies to every table in the namespace and the namespaces under it that
    no nearer namespace or table policy of the same kind covers, and it is nearer than the catalog's.
    Attaching replaces the policy of its kind already attached; detaching names the policy it expects.

    ``version`` is the stored version the namespace was read at, 1 until its first save. Only the
    repository moves it, refusing a save made from a copy read at an older version.
    """

    id: NamespaceId
    discovery_policy_id: TableDiscoveryPolicyId | None = None
    maintenance_policy_id: TableMaintenancePolicyId | None = None
    version: PositiveInt = 1
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(cls, id: NamespaceId, now: datetime) -> Namespace:  # noqa: A002
        """Register a namespace that holds no policy yet, at version 1."""
        return cls(id=id, created_at=now, updated_at=now)

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the namespace."""
        return self.id.catalog

    @property
    def levels(self) -> tuple[str, ...]:
        """Return the levels of the namespace, outermost first."""
        return self.id.levels

    @property
    def holds_any_policy(self) -> bool:
        """Return whether a discovery or a maintenance policy is attached to the namespace."""
        return self.discovery_policy_id is not None or self.maintenance_policy_id is not None

    def attach_discovery_policy(self, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        """Attach the discovery policy, replacing the one attached; idempotent for the attached one."""
        if self.discovery_policy_id == policy_id:
            return
        self._assign_together(discovery_policy_id=policy_id, updated_at=now)

    def detach_discovery_policy(self, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        """Detach the discovery policy; raise ``PolicyNotAttached`` unless it is the one attached."""
        if self.discovery_policy_id != policy_id:
            raise PolicyNotAttached(f"discovery policy {policy_id} is not attached to {self._described()}")
        self._assign_together(discovery_policy_id=None, updated_at=now)

    def attach_maintenance_policy(self, policy_id: TableMaintenancePolicyId, now: datetime) -> None:
        """Attach the maintenance policy, replacing the one attached; idempotent for the attached one."""
        if self.maintenance_policy_id == policy_id:
            return
        self._assign_together(maintenance_policy_id=policy_id, updated_at=now)

    def detach_maintenance_policy(self, policy_id: TableMaintenancePolicyId, now: datetime) -> None:
        """Detach the maintenance policy; raise ``PolicyNotAttached`` unless it is the one attached."""
        if self.maintenance_policy_id != policy_id:
            raise PolicyNotAttached(f"maintenance policy {policy_id} is not attached to {self._described()}")
        self._assign_together(maintenance_policy_id=None, updated_at=now)

    def _described(self) -> str:
        return f"namespace {'.'.join(self.levels)} of {self.catalog}"
