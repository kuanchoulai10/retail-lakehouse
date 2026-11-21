"""Define the TableDiscoveryRule value object."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Self

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_condition import (
    DiscoveryCondition,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_outcome import (
    DiscoveryOutcome,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


class TableDiscoveryRule(ValueObject):
    """One rule of a discovery policy: the outcome it gives a table that every one of its conditions matches.

    A version never changes, so its rules are values; the ``dr-`` id links a rule across versions. A rule
    has at least one condition, and each attribute appears in at most one of them.
    """

    id: TableDiscoveryRuleId
    outcome: DiscoveryOutcome
    conditions: tuple[DiscoveryCondition, ...]

    @model_validator(mode="after")
    def _conditions_are_distinct(self) -> Self:
        if not self.conditions:
            raise ValueError("a discovery rule needs at least one condition")
        for attribute, count in Counter(condition.attribute for condition in self.conditions).items():
            if count > 1:
                raise ValueError(f"attribute {attribute.value} appears more than once in a discovery rule")
        return self

    def matches(self, name: TableName) -> bool:
        """Return whether every condition holds for the table."""
        return all(condition.matches(name) for condition in self.conditions)
