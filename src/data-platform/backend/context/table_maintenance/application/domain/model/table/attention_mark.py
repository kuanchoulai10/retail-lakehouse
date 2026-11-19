"""Define the AttentionMark value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.table.applied_policy_ref import (
    AppliedPolicyRef,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)


class AttentionMark(ValueObject):
    """Mark an operation of a table as needing a person, why, and under which applicable policy.

    ``policy`` points at the policy by id, version and target; it alone decides whether the mark
    still holds. ``policy_name`` is a display-only copy of that policy's name when the mark was
    set, so a mark under a policy deleted since still reads by name.
    """

    since: datetime
    reason: str
    policy: AppliedPolicyRef
    policy_name: TableMaintenancePolicyName
