"""Define the TableDiscoveryPolicyVersion value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_policy_content import (
    DiscoveryPolicyContent,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_id import (
    TableDiscoveryPolicyId,
)


class TableDiscoveryPolicyVersion(ValueObject):
    """One immutable version of a discovery policy's content, belonging to its policy by id."""

    policy_id: TableDiscoveryPolicyId
    version: PositiveInt
    content: DiscoveryPolicyContent
    created_at: datetime
