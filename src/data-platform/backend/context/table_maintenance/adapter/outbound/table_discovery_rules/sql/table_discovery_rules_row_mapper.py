"""Define the TableDiscoveryRulesRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_discovery_rules import (
    GlobList,
    RuleAction,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TableDiscoveryRules,
    TableDiscoveryRulesId,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import RowMapping


class TableDiscoveryRulesRowMapper:
    """Convert between the TableDiscoveryRules aggregate and its list and rule rows."""

    @staticmethod
    def to_list_values(rules: TableDiscoveryRules) -> dict[str, Any]:
        """Return the columns of the list row."""
        return {"id": rules.id.value, "version": rules.version}

    @staticmethod
    def to_rule_values(rules: TableDiscoveryRules) -> list[dict[str, Any]]:
        """Return the columns of each rule row."""
        return [
            {
                "rules_id": rules.id.value,
                "id": rule.id.value,
                "priority": rule.priority,
                "action": rule.action.value,
                "enabled": rule.enabled,
                "catalogs_json": list(rule.catalogs.globs),
                "namespaces_json": list(rule.namespaces.globs),
                "tables_json": list(rule.tables.globs),
                "created_at": rule.created_at,
                "updated_at": rule.updated_at,
            }
            for rule in rules.rules
        ]

    @staticmethod
    def to_aggregate(list_row: RowMapping, rule_rows: Sequence[RowMapping]) -> TableDiscoveryRules:
        """Rebuild the aggregate from its list row and its rule rows in priority order."""
        return TableDiscoveryRules(
            id=TableDiscoveryRulesId(list_row["id"]),
            version=list_row["version"],
            rules=tuple(
                TableDiscoveryRule(
                    id=TableDiscoveryRuleId(row["id"]),
                    priority=row["priority"],
                    action=RuleAction(row["action"]),
                    enabled=row["enabled"],
                    catalogs=GlobList(globs=tuple(row["catalogs_json"])),
                    namespaces=GlobList(globs=tuple(row["namespaces_json"])),
                    tables=GlobList(globs=tuple(row["tables_json"])),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rule_rows
            ),
        )
