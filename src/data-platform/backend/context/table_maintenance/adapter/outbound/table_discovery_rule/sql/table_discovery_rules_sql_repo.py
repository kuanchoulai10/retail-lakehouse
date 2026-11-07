"""Define the TableDiscoveryRulesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_discovery_rule.sql.table_discovery_rule_row_mapper import (
    TableDiscoveryRuleRowMapper,
)
from context.table_maintenance.adapter.outbound.table_discovery_rule.sql.table_discovery_rules_table import (
    table_discovery_rules_table as t,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_discovery_rule import (
    TableDiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRule,
        TableMaintenancePresetId,
    )
    from base import EntityId


class TableDiscoveryRulesSqlRepo(TableDiscoveryRulesRepo):
    """Store TableDiscoveryRule aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableDiscoveryRule) -> TableDiscoveryRule:
        """Insert a new rule."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**TableDiscoveryRuleRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryRule | None:
        """Return the rule with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else TableDiscoveryRuleRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[TableDiscoveryRule]:
        """Return all rules ordered by (priority, id)."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.priority, t.c.id)).all()
        return [TableDiscoveryRuleRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, rule: TableDiscoveryRule) -> TableDiscoveryRule:
        """Persist the changed rule."""
        values = TableDiscoveryRuleRowMapper.to_values(rule)
        with self._engine.begin() as conn:
            result = conn.execute(update(t).where(t.c.id == rule.id.value).values(**values))
            if result.rowcount == 0:
                raise LookupError(f"discovery rule {rule.id.value} does not exist")
        return rule

    def delete(self, entity_id: EntityId) -> None:
        """Delete the rule with the given id."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.id == entity_id.value))

    def count_by_preset(self, preset_id: TableMaintenancePresetId) -> int:
        """Return how many rules reference the preset."""
        stmt = select(func.count()).select_from(t).where(t.c.preset_id == preset_id.value)
        with self._engine.connect() as conn:
            return int(conn.execute(stmt).scalar_one())
