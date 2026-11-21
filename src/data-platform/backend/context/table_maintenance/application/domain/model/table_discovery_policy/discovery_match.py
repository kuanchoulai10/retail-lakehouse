"""Define the DiscoveryMatch value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.default_discovery_policy_id import (
    DEFAULT_DISCOVERY_POLICY_ID,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_id import (
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)


class DiscoveryMatch(ValueObject):
    """Name what decided a table: the policy, its version and the deciding rule, or None for the no-match outcome."""

    policy_id: TableDiscoveryPolicyId
    policy_version: PositiveInt
    rule_id: TableDiscoveryRuleId | None

    @classmethod
    def platform_default(cls) -> DiscoveryMatch:
        """Return the platform default at version 1, its only version, with no rule: what nothing attached decides."""
        return cls(policy_id=DEFAULT_DISCOVERY_POLICY_ID, policy_version=1, rule_id=None)
