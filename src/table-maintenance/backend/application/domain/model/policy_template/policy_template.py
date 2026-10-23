"""Define the PolicyTemplate aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from base.aggregate_root import AggregateRoot


@dataclass(eq=False)
class PolicyTemplate(AggregateRoot[PolicyTemplateId]):
    """A named, reusable set of maintenance settings."""

    id: PolicyTemplateId
    name: str
    settings: MaintenanceSettings
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        id: PolicyTemplateId,  # noqa: A002
        name: str,
        settings: MaintenanceSettings,
        now: datetime,
    ) -> PolicyTemplate:
        """Create a template."""
        return cls(id=id, name=name, settings=settings, created_at=now, updated_at=now)

    def rename(self, name: str, now: datetime) -> None:
        """Rename the template."""
        self.name = name
        self.updated_at = now

    def update_settings(self, settings: MaintenanceSettings, now: datetime) -> None:
        """Replace the template's settings."""
        self.settings = settings
        self.updated_at = now
