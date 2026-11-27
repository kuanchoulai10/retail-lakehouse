"""Define the TableDiscoveryPolicyVersion value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.discovery_rules import (
    DiscoveryRules,
)


class TableDiscoveryPolicyVersion(ValueObject):
    """One immutable version of a discovery policy's description and rules, belonging to its policy by id."""

    policy_id: TableDiscoveryPolicyId
    version: PositiveInt
    description: str
    rules: DiscoveryRules
    created_at: datetime
