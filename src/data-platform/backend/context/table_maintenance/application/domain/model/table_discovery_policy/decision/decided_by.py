"""Define the DecidedBy value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId


class DecidedBy(ValueObject):
    """Name what decided a table: the policy, its version and the position of the deciding rule.

    The position (1-based) is None when the policy applies but none of its rules matched the table.
    """

    policy_id: TableDiscoveryPolicyId
    policy_version: PositiveInt
    rule_position: PositiveInt | None
