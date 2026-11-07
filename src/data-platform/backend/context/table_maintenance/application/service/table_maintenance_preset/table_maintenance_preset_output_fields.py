"""Define the table_maintenance_preset_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.service.shared import (
    maintenance_settings_to_dict,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table_maintenance_preset import (
        TableMaintenancePreset,
    )


def table_maintenance_preset_output_fields(
    preset: TableMaintenancePreset,
) -> dict[str, Any]:
    """Return the primitive fields shared by every table maintenance preset output."""
    return {
        "id": preset.id.value,
        "name": preset.name,
        "settings": maintenance_settings_to_dict(preset.settings),
        "created_at": preset.created_at,
        "updated_at": preset.updated_at,
    }
