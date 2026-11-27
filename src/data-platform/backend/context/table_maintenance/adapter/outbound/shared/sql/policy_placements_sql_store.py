"""Define the PolicyPlacementsSqlStore."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, cast, column, literal, null, select, table, union_all

from context.table_maintenance.application.port.outbound.shared import (
    PolicyPlacement,
    PolicyPlacementsStore,
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.port.outbound.table import TableStatus

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement, Engine, Row, Select

    from base import EntityId

_POLICY_COLUMNS = ("discovery_policy_id", "maintenance_policy_id")
_catalogs = table("catalogs", column("name"), *(column(c) for c in _POLICY_COLUMNS))
_namespaces = table("namespaces", column("id"), column("catalog"), *(column(c) for c in _POLICY_COLUMNS))
_tables = table(
    "tables",
    column("uuid"),
    column("catalog"),
    column("namespace"),
    column("table_name"),
    column("status"),
    *(column(c) for c in _POLICY_COLUMNS),
)
_SEPARATOR = "\x1f"
_TYPE_ORDER = {PolicyTargetType.CATALOG: 0, PolicyTargetType.NAMESPACE: 1, PolicyTargetType.TABLE: 2}


class PolicyPlacementsSqlStore(PolicyPlacementsStore):
    """Read the policy placements from the policy columns of the catalogs, namespaces and tables rows.

    Each read is one ``UNION ALL`` over the three tables, leaving out dropped tables. It names the
    tables by name only, so this module needs none of the aggregate SQL packages.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the store to an engine."""
        self._engine = engine

    def discovery_placements(self, policy_id: EntityId) -> tuple[PolicyPlacement, ...]:
        """Return every place the discovery policy is attached to, by type and then path."""
        return self._placements("discovery_policy_id", policy_id.value)

    def maintenance_placements(self, policy_id: EntityId) -> tuple[PolicyPlacement, ...]:
        """Return every place the maintenance policy is attached to, by type and then path."""
        return self._placements("maintenance_policy_id", policy_id.value)

    def catalogs_with_discovery_policy(self) -> frozenset[str]:
        """Return each catalog where a discovery policy is attached to it, a namespace or a live table of it."""
        held = "discovery_policy_id"
        stmt = union_all(
            select(_catalogs.c.name.label("catalog")).where(_catalogs.c[held].is_not(None)),
            select(_namespaces.c.catalog).where(_namespaces.c[held].is_not(None)),
            select(_tables.c.catalog).where(_tables.c[held].is_not(None), _live()),
        )
        with self._engine.connect() as conn:
            return frozenset(row[0] for row in conn.execute(stmt))

    def _placements(self, held: str, policy_id: str) -> tuple[PolicyPlacement, ...]:
        stmt = union_all(
            _row(PolicyTargetType.CATALOG, _catalogs.c.name).where(_catalogs.c[held] == policy_id),
            _row(PolicyTargetType.NAMESPACE, _namespaces.c.id).where(_namespaces.c[held] == policy_id),
            select(
                literal(PolicyTargetType.TABLE.value).label("type"),
                _tables.c.catalog.label("place"),
                _tables.c.namespace,
                _tables.c.table_name,
                _tables.c.uuid,
            ).where(_tables.c[held] == policy_id, _live()),
        )
        with self._engine.connect() as conn:
            placements = [_placement(row) for row in conn.execute(stmt)]
        return tuple(sorted(placements, key=lambda p: (_TYPE_ORDER[p.target.type], p.target.path)))


def _live() -> ColumnElement[bool]:
    return _tables.c.status != TableStatus.DROPPED.value


def _row(type_: PolicyTargetType, place: ColumnElement[str]) -> Select:
    """Select a catalog or namespace row in the union's shape, its table columns NULL."""
    empty = cast(null(), String)
    return select(
        literal(type_.value).label("type"),
        place.label("place"),
        empty.label("namespace"),
        empty.label("table_name"),
        empty.label("uuid"),
    )


def _placement(row: Row) -> PolicyPlacement:
    type_ = PolicyTargetType(row.type)
    if type_ == PolicyTargetType.CATALOG:
        return PolicyPlacement(target=PolicyTarget(type=type_, path=(row.place,)))
    if type_ == PolicyTargetType.NAMESPACE:
        return PolicyPlacement(target=PolicyTarget(type=type_, path=tuple(row.place.split(_SEPARATOR))))
    path = (row.place, *row.namespace.split("."), row.table_name)
    return PolicyPlacement(target=PolicyTarget(type=type_, path=path, table_uuid=row.uuid))
