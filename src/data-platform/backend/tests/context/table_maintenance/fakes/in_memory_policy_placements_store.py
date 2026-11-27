"""Define the InMemoryPolicyPlacementsStore fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    PolicyPlacement,
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore

if TYPE_CHECKING:
    from base import EntityId
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import TablesRepo

_TYPE_ORDER = {PolicyTargetType.CATALOG: 0, PolicyTargetType.NAMESPACE: 1, PolicyTargetType.TABLE: 2}


class InMemoryPolicyPlacementsStore(PolicyPlacementsStore):
    """Answer from the catalogs, namespaces and tables repos it is given, never from a list of its own.

    So a service that attaches, detaches or deletes through those repos is answered by what they
    now hold, exactly as the SQL store reads the rows the SQL repos wrote.
    """

    def __init__(self, catalogs: CatalogsRepo, namespaces: NamespacesRepo, tables: TablesRepo) -> None:
        """Read the three holder repos."""
        self._catalogs = catalogs
        self._namespaces = namespaces
        self._tables = tables

    def discovery_placements(self, policy_id: EntityId) -> tuple[PolicyPlacement, ...]:
        """Return each place holding the discovery policy, by type and then path."""
        return self._placements("discovery_policy_id", policy_id)

    def maintenance_placements(self, policy_id: EntityId) -> tuple[PolicyPlacement, ...]:
        """Return each place holding the maintenance policy, by type and then path."""
        return self._placements("maintenance_policy_id", policy_id)

    def catalogs_with_discovery_policy(self) -> frozenset[str]:
        """Return each catalog where it, a namespace or a live table of it holds a discovery policy."""
        return frozenset(target.path[0] for target, held in self._held() if held[0] is not None)

    def _placements(self, kind: str, policy_id: EntityId) -> tuple[PolicyPlacement, ...]:
        index = 0 if kind == "discovery_policy_id" else 1
        targets = [target for target, held in self._held() if held[index] == policy_id]
        ordered = sorted(targets, key=lambda t: (_TYPE_ORDER[t.type], t.path))
        return tuple(PolicyPlacement(target=target) for target in ordered)

    def _held(self) -> list[tuple[PolicyTarget, tuple[EntityId | None, EntityId | None]]]:
        held: list[tuple[PolicyTarget, tuple[EntityId | None, EntityId | None]]] = [
            (
                PolicyTarget(type=PolicyTargetType.CATALOG, path=(c.id.value,)),
                (c.discovery_policy_id, c.maintenance_policy_id),
            )
            for c in self._catalogs.list_all()
        ]
        held += [
            (
                PolicyTarget(type=PolicyTargetType.NAMESPACE, path=(n.catalog, *n.levels)),
                (n.discovery_policy_id, n.maintenance_policy_id),
            )
            for n in self._namespaces.list_all()
        ]
        held += [
            (
                PolicyTarget(
                    type=PolicyTargetType.TABLE,
                    path=(t.name.catalog, *t.name.namespace.split("."), t.name.table),
                    table_uuid=t.id.value,
                ),
                (t.discovery_policy_id, t.maintenance_policy_id),
            )
            for t in self._tables.list_all()
            if t.status != TableStatus.DROPPED
        ]
        return held
