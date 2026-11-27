"""Define the PolicyPlacementsStore outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Store

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import (
        PolicyPlacement,
        TableDiscoveryPolicyId,
        TableMaintenancePolicyId,
    )


class PolicyPlacementsStore(Store):
    """Read where policies are attached, across the catalogs, namespaces and tables that hold them.

    A read model over the places: each holds at most one policy of each kind, so a policy is placed
    once per place it is attached to. A dropped table holds no policy, so it places none. The
    placements come back ordered by type (catalog, namespace, table) and then by path.
    """

    @abstractmethod
    def discovery_placements(self, policy_id: TableDiscoveryPolicyId) -> tuple[PolicyPlacement, ...]:
        """Return every place the discovery policy is attached to."""

    @abstractmethod
    def maintenance_placements(self, policy_id: TableMaintenancePolicyId) -> tuple[PolicyPlacement, ...]:
        """Return every place the maintenance policy is attached to."""

    @abstractmethod
    def catalogs_with_discovery_policy(self) -> frozenset[str]:
        """Return each catalog where a discovery policy is attached: to it, to a namespace or to a table of it."""
