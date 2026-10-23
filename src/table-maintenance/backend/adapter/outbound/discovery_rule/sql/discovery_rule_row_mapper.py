"""Define the DiscoveryRuleRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class DiscoveryRuleRowMapper:
    """Convert between DiscoveryRule aggregates and table rows."""

    @staticmethod
    def to_values(rule: DiscoveryRule) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": rule.id.value,
            "priority": rule.priority,
            "effect": rule.effect.value,
            "pattern_catalog": rule.pattern.catalog,
            "pattern_namespace": rule.pattern.namespace,
            "pattern_table": rule.pattern.table,
            "template_id": None if rule.template_id is None else rule.template_id.value,
            "enabled": rule.enabled,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> DiscoveryRule:
        """Rebuild the aggregate from a row without registering events."""
        template_id = row["template_id"]
        return DiscoveryRule(
            id=DiscoveryRuleId(row["id"]),
            priority=row["priority"],
            effect=RuleEffect(row["effect"]),
            pattern=TablePattern(
                catalog=row["pattern_catalog"],
                namespace=row["pattern_namespace"],
                table=row["pattern_table"],
            ),
            template_id=None if template_id is None else PolicyTemplateId(template_id),
            enabled=row["enabled"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
