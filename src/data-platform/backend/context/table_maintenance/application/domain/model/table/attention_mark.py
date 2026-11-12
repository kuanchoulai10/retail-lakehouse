"""Define the AttentionMark value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.table.applied_policy_ref import (
    AppliedPolicyRef,
)


class AttentionMark(ValueObject):
    """Mark an operation of a table as needing a person, why, and under which applicable policy."""

    since: datetime
    reason: str
    policy: AppliedPolicyRef
