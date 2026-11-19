"""Define the AppliedPolicyRef value object."""

from __future__ import annotations

from typing import Any

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
)


class AppliedPolicyRef(ValueObject):
    """Point at the maintenance policy that applied to a table: its id, version and the target it is attached to.

    ``target`` is None for the platform default policy, which is attached to nothing.
    """

    policy_id: TableMaintenancePolicyId
    version: int
    target: dict[str, Any] | None = None
