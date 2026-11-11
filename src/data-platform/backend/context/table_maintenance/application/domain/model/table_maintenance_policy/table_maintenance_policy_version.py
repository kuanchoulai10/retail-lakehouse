"""Define the TableMaintenancePolicyVersion value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.maintenance_policy_content import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.table_maintenance_policy_name import (
    TableMaintenancePolicyName,
)


class TableMaintenancePolicyVersion(ValueObject):
    """One immutable version of a policy's content."""

    name: TableMaintenancePolicyName
    version: PositiveInt
    content: MaintenancePolicyContent
    created_at: datetime
