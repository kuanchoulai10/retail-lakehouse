"""Define the TableMaintenancePresetRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.sql.maintenance_settings_codec import MaintenanceSettingsCodec
from application.domain.model.table_maintenance_preset.table_maintenance_preset import (
    TableMaintenancePreset,
)
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableMaintenancePresetRowMapper:
    """Convert between TableMaintenancePreset aggregates and table rows."""

    @staticmethod
    def to_values(preset: TableMaintenancePreset) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "id": preset.id.value,
            "name": preset.name,
            "settings_json": MaintenanceSettingsCodec.encode(preset.settings),
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> TableMaintenancePreset:
        """Rebuild the aggregate from a row without registering events."""
        return TableMaintenancePreset(
            id=TableMaintenancePresetId(row["id"]),
            name=row["name"],
            settings=MaintenanceSettingsCodec.decode(row["settings_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
