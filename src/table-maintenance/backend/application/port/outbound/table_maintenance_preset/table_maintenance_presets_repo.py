"""Define the TableMaintenancePresetsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from application.domain.model.table_maintenance_preset.table_maintenance_preset import (
    TableMaintenancePreset,
)
from base.entity_id import EntityId
from base.repository import Repository


class TableMaintenancePresetsRepo(Repository[TableMaintenancePreset]):
    """Persist and query TableMaintenancePreset aggregates."""

    @abstractmethod
    def update(self, preset: TableMaintenancePreset) -> TableMaintenancePreset:
        """Persist the changed preset and return it."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the preset with the given id."""

    @abstractmethod
    def find_by_name(self, name: str) -> TableMaintenancePreset | None:
        """Return the preset with exactly this name, or None."""
