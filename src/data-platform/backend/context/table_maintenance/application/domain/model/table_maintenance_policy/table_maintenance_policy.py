"""Define the TableMaintenancePolicy aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import PositiveInt

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import TableMaintenancePolicyId
from context.table_maintenance.application.domain.model.table_maintenance_policy.default_policy_id import (
    DEFAULT_POLICY_ID,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.default_policy_name import (
    DEFAULT_POLICY_NAME,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.maintenance_policy_content import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.stale_policy_version import (
    StalePolicyVersion,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.table_maintenance_policy_name import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.table_maintenance_policy_version import (  # noqa: E501
    TableMaintenancePolicyVersion,
)


class TableMaintenancePolicy(AggregateRoot[TableMaintenancePolicyId]):
    """A versioned maintenance policy; each replacement makes a new version.

    It is identified by its ``mp-`` id; its unique ``name`` is for display and URLs.
    """

    id: TableMaintenancePolicyId
    name: TableMaintenancePolicyName
    content: MaintenancePolicyContent
    version: PositiveInt
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        name: TableMaintenancePolicyName,
        content: MaintenancePolicyContent,
        now: datetime,
    ) -> TableMaintenancePolicy:
        """Create a policy at version 1, under a new ``mp-`` id."""
        return cls(
            id=TableMaintenancePolicyId.new(), name=name, content=content, version=1, created_at=now, updated_at=now
        )

    @classmethod
    def create_default(cls, now: datetime) -> TableMaintenancePolicy:
        """Create the default policy at version 1: the fixed id, the name ``default`` and the platform content."""
        return cls(
            id=DEFAULT_POLICY_ID,
            name=TableMaintenancePolicyName(value=DEFAULT_POLICY_NAME),
            content=MaintenancePolicyContent.platform_default(),
            version=1,
            created_at=now,
            updated_at=now,
        )

    def replace(self, content: MaintenancePolicyContent, expected_version: int, now: datetime) -> None:
        """Replace the content as a new version; reject a stale ``expected_version``."""
        if expected_version != self.version:
            raise StalePolicyVersion(f"policy {self.name.value} is at version {self.version}, not {expected_version}")
        self._assign_together(content=content, version=self.version + 1, updated_at=now)

    def current_version(self) -> TableMaintenancePolicyVersion:
        """Return the current content as a version record."""
        return TableMaintenancePolicyVersion(
            policy_id=self.id, version=self.version, content=self.content, created_at=self.updated_at
        )

    @property
    def is_default(self) -> bool:
        """Return whether this is the default policy, told by its fixed id."""
        return self.id == DEFAULT_POLICY_ID
