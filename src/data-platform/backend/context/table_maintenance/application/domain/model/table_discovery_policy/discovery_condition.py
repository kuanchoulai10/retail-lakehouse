"""Define the DiscoveryCondition value object."""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from pydantic import field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.condition_operator import (
    ConditionOperator,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_attribute import (
    DiscoveryAttribute,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


class DiscoveryCondition(ValueObject):
    """One condition of a discovery rule: the attribute it reads, how it matches and the values it matches.

    Shaped like a Kubernetes ``matchExpressions`` entry, so a later attribute or operator adds a value,
    not a structure. The values are alternatives: the condition holds when any of them matches. A
    ``glob`` matches case-sensitively (``fnmatchcase``), and on the dot-joined namespace ``*`` crosses dots.
    """

    attribute: DiscoveryAttribute
    operator: ConditionOperator
    values: tuple[str, ...]

    @field_validator("values")
    @classmethod
    def _non_empty(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("a discovery condition needs at least one value")
        if any(not value for value in values):
            raise ValueError("a discovery condition value must not be empty")
        return values

    def matches(self, name: TableName) -> bool:
        """Return whether any value matches the attribute this condition reads of the table."""
        match self.attribute:
            case DiscoveryAttribute.NAMESPACE:
                subject = name.namespace
            case DiscoveryAttribute.TABLE_NAME:
                subject = name.table
        return any(fnmatchcase(subject, glob) for glob in self.values)
