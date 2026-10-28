"""Define the InMemoryTableMaintenancePresetsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.exceptions import ConflictError
from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
    TableMaintenancePresetsRepo,
)

if TYPE_CHECKING:
    from application.domain.model.table_maintenance_preset.table_maintenance_preset import (
        TableMaintenancePreset,
    )
    from base.entity_id import EntityId


class InMemoryTableMaintenancePresetsRepo(TableMaintenancePresetsRepo):
    """Keep presets in a dict, enforcing unique names like the SQL repo."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMaintenancePreset] = {}

    def create(self, entity: TableMaintenancePreset) -> TableMaintenancePreset:
        """Insert a preset; a duplicate name raises ConflictError."""
        if any(t.name == entity.name for t in self.items.values()):
            raise ConflictError(f"preset name {entity.name!r} exists")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePreset | None:
        """Return the preset or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableMaintenancePreset]:
        """Return presets ordered by name."""
        return sorted(self.items.values(), key=lambda t: t.name)

    def update(self, preset: TableMaintenancePreset) -> TableMaintenancePreset:
        """Replace a stored preset."""
        if preset.id.value not in self.items:
            raise LookupError(
                f"table maintenance preset {preset.id.value} does not exist"
            )
        self.items[preset.id.value] = preset
        return preset

    def delete(self, entity_id: EntityId) -> None:
        """Remove a preset if present."""
        self.items.pop(entity_id.value, None)

    def find_by_name(self, name: str) -> TableMaintenancePreset | None:
        """Return the preset with this exact name."""
        return next((t for t in self.items.values() if t.name == name), None)
