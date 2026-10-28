"""Define the TableDiscoveryRuleRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from application.domain.model.table_discovery_rule import (
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    RuleEffect,
    TablePattern,
)
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableDiscoveryRuleRowMapper:
    """Convert between TableDiscoveryRule aggregates and table rows."""

    @staticmethod
    def to_values(rule: TableDiscoveryRule) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": rule.id.value,
            "priority": rule.priority,
            "effect": rule.effect.value,
            "pattern_catalog": rule.pattern.catalog,
            "pattern_namespace": rule.pattern.namespace,
            "pattern_table": rule.pattern.table,
            "preset_id": None if rule.preset_id is None else rule.preset_id.value,
            "enabled": rule.enabled,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableDiscoveryRule:
        """Rebuild the aggregate from a row without registering events."""
        preset_id = row["preset_id"]
        return TableDiscoveryRule(
            id=TableDiscoveryRuleId(row["id"]),
            priority=row["priority"],
            effect=RuleEffect(row["effect"]),
            pattern=TablePattern(
                catalog=row["pattern_catalog"],
                namespace=row["pattern_namespace"],
                table=row["pattern_table"],
            ),
            preset_id=None
            if preset_id is None
            else TableMaintenancePresetId(preset_id),
            enabled=row["enabled"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
