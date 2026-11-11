"""Define the TableDiscoveryRulesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_discovery_rules.sql.table_discovery_rule_items_table import (
    table_discovery_rule_items_table as items,
)
from context.table_maintenance.adapter.outbound.table_discovery_rules.sql.table_discovery_rules_row_mapper import (
    TableDiscoveryRulesRowMapper,
)
from context.table_maintenance.adapter.outbound.table_discovery_rules.sql.table_discovery_rules_table import (
    table_discovery_rules_table as lists,
)
from context.table_maintenance.application.port.outbound.table_discovery_rules import (
    GLOBAL_TABLE_DISCOVERY_RULES_ID,
    StaleDiscoveryRulesVersion,
    TableDiscoveryRules,
    TableDiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

    from base import EntityId


class TableDiscoveryRulesSqlRepo(TableDiscoveryRulesRepo):
    """Store the discovery rules in a SQL database: a list row with its version, and one row per rule."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableDiscoveryRules) -> TableDiscoveryRules:
        """Store a list that was never saved; a stored one raises StaleDiscoveryRulesVersion."""
        return self.save(entity)

    def get(self, entity_id: EntityId) -> TableDiscoveryRules | None:
        """Return the list with the given id, or None when it is not the singleton."""
        if entity_id != GLOBAL_TABLE_DISCOVERY_RULES_ID:
            return None
        return self.get_rules()

    def list_all(self) -> list[TableDiscoveryRules]:
        """Return the one list."""
        return [self.get_rules()]

    def get_rules(self) -> TableDiscoveryRules:
        """Return the rules in priority order; empty at version 0 before the first save."""
        rules_id = GLOBAL_TABLE_DISCOVERY_RULES_ID.value
        with self._engine.connect() as conn:
            list_row = conn.execute(select(lists).where(lists.c.id == rules_id)).first()
            if list_row is None:
                return TableDiscoveryRules.empty()
            rule_rows = conn.execute(select(items).where(items.c.rules_id == rules_id).order_by(items.c.priority)).all()
        return TableDiscoveryRulesRowMapper.to_aggregate(list_row._mapping, [r._mapping for r in rule_rows])

    def save(self, rules: TableDiscoveryRules) -> TableDiscoveryRules:
        """Replace the list row's version and every rule row in one transaction, from ``rules.version - 1``."""
        try:
            with self._engine.begin() as conn:
                self._advance_version(conn, rules)
                conn.execute(delete(items).where(items.c.rules_id == rules.id.value))
                values = TableDiscoveryRulesRowMapper.to_rule_values(rules)
                if values:
                    conn.execute(insert(items), values)
        except IntegrityError as exc:
            raise StaleDiscoveryRulesVersion(f"discovery rules were changed concurrently: {exc.orig}") from exc
        return rules

    @staticmethod
    def _advance_version(conn: Connection, rules: TableDiscoveryRules) -> None:
        values = TableDiscoveryRulesRowMapper.to_list_values(rules)
        previous = rules.version - 1
        if previous == 0:
            conn.execute(insert(lists).values(**values))
            return
        result = conn.execute(
            update(lists).where(lists.c.id == rules.id.value, lists.c.version == previous).values(**values)
        )
        if result.rowcount == 0:
            raise StaleDiscoveryRulesVersion(f"discovery rules are no longer at version {previous}")
