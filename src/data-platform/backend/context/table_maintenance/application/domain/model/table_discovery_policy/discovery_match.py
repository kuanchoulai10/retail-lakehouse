"""Define the DiscoveryMatch value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
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
