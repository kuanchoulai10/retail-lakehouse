"""Define the policy_holders_nearest_first domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace
    from context.table_maintenance.application.domain.model.table import Table, TableName


def policy_holders_nearest_first(
    table: Table | None,
    namespaces: Sequence[Namespace],
    catalog: Catalog | None,
    *,
    name: TableName | None = None,
) -> tuple[tuple[PolicyTarget, Table | Namespace | Catalog], ...]:
    """Return the places that may hold a policy for a place, nearest first, each with its target.

    The walk is the table, then the namespaces deepest first (by their number of levels), then the
    catalog. ``name`` is where the table is now, its stored name by default: a table read under a new
    name is placed by it. With a table, a namespace that does not enclose it (another catalog, a
    sibling, a deeper one) and a catalog of another name are left out; without one, every namespace
    and the catalog given are walked.
    """
    current = name if name is not None else (None if table is None else table.name)
    walk: list[tuple[PolicyTarget, Table | Namespace | Catalog]] = []
    if table is not None and current is not None:
        path = (current.catalog, *current.namespace.split("."), current.table)
        walk.append((PolicyTarget(type=PolicyTargetType.TABLE, path=path, table_uuid=table.id.value), table))
    enclosing = None if current is None else (current.catalog, *current.namespace.split("."))
    for namespace in sorted(namespaces, key=lambda n: len(n.levels), reverse=True):
        path = (namespace.catalog, *namespace.levels)
        if enclosing is not None and enclosing[: len(path)] != path:
            continue
        walk.append((PolicyTarget(type=PolicyTargetType.NAMESPACE, path=path), namespace))
    if catalog is not None and (current is None or catalog.id.value == current.catalog):
        walk.append((PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog.id.value,)), catalog))
    return tuple(walk)
