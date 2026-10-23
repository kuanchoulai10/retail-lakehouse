"""Define the PolicyTemplateRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.sql.maintenance_settings_codec import MaintenanceSettingsCodec
from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class PolicyTemplateRowMapper:
    """Convert between PolicyTemplate aggregates and table rows."""

    @staticmethod
    def to_values(template: PolicyTemplate) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": template.id.value,
            "name": template.name,
            "settings_json": MaintenanceSettingsCodec.encode(template.settings),
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> PolicyTemplate:
        """Rebuild the aggregate from a row without registering events."""
        return PolicyTemplate(
            id=PolicyTemplateId(row["id"]),
            name=row["name"],
            settings=MaintenanceSettingsCodec.decode(row["settings_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
