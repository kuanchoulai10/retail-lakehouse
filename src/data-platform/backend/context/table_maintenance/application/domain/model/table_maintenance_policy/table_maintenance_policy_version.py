"""Define the TableMaintenancePolicyVersion value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.maintenance_policy_content import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.table_maintenance_policy_id import (
    TableMaintenancePolicyId,
)


class TableMaintenancePolicyVersion(ValueObject):
    """One immutable version of a policy's content, belonging to its policy by id."""

    policy_id: TableMaintenancePolicyId
    version: PositiveInt
    content: MaintenancePolicyContent
    created_at: datetime
