"""Define the Catalog aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt, model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    PolicyNotAttached,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)


class Catalog(AggregateRoot[CatalogId]):
    """Hold the discovery policy and the maintenance policy attached to one catalog, at most one of each.

    A policy attached here applies to every table of the catalog that no nearer namespace or table
    policy of the same kind covers. Attaching a policy replaces the one of its kind already attached,
    and detaching names the policy it expects, so a stale view cannot detach a policy someone attached since.

    ``version`` is the stored version the catalog was read at, 1 until its first save. Only the
    repository moves it: a save made from a copy read at an older version is refused, so of two
    people attaching a discovery and a maintenance policy at once, neither write is lost.
    """

    id: CatalogId
    discovery_policy_id: TableDiscoveryPolicyId | None = None
    maintenance_policy_id: TableMaintenancePolicyId | None = None
    version: PositiveInt = 1
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _names_a_catalog(self) -> Catalog:
        if not self.id.value:
            raise ValueError("a catalog needs a name")
        return self

    @classmethod
    def register(cls, id: CatalogId, now: datetime) -> Catalog:  # noqa: A002
        """Register a catalog that holds no policy yet, at version 1."""
        return cls(id=id, created_at=now, updated_at=now)

    @property
    def holds_any_policy(self) -> bool:
        """Return whether a discovery or a maintenance policy is attached to the catalog."""
        return self.discovery_policy_id is not None or self.maintenance_policy_id is not None

    def attach_discovery_policy(self, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        """Attach the discovery policy, replacing the one attached; idempotent for the attached one."""
        if self.discovery_policy_id == policy_id:
            return
        self._assign_together(discovery_policy_id=policy_id, updated_at=now)

    def detach_discovery_policy(self, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        """Detach the discovery policy; raise ``PolicyNotAttached`` unless it is the one attached."""
        if self.discovery_policy_id != policy_id:
            raise PolicyNotAttached(f"discovery policy {policy_id} is not attached to catalog {self.id}")
        self._assign_together(discovery_policy_id=None, updated_at=now)

    def attach_maintenance_policy(self, policy_id: TableMaintenancePolicyId, now: datetime) -> None:
        """Attach the maintenance policy, replacing the one attached; idempotent for the attached one."""
        if self.maintenance_policy_id == policy_id:
            return
        self._assign_together(maintenance_policy_id=policy_id, updated_at=now)

    def detach_maintenance_policy(self, policy_id: TableMaintenancePolicyId, now: datetime) -> None:
        """Detach the maintenance policy; raise ``PolicyNotAttached`` unless it is the one attached."""
        if self.maintenance_policy_id != policy_id:
            raise PolicyNotAttached(f"maintenance policy {policy_id} is not attached to catalog {self.id}")
        self._assign_together(maintenance_policy_id=None, updated_at=now)
