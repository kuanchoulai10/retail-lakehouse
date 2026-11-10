"""Define the TableMaintenancePresetsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
)

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId


class TableMaintenancePresetsRepo(Repository[TableMaintenancePreset]):
    """Persist and query TableMaintenancePreset aggregates."""

    @abstractmethod
    def get(self, entity_id: EntityId | ModelEntityId) -> TableMaintenancePreset | None:
        """Return the preset with the given id, or None when it does not exist."""

    @abstractmethod
    def update(self, preset: TableMaintenancePreset) -> TableMaintenancePreset:
        """Persist the changed preset and return it."""

    @abstractmethod
    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Delete the preset with the given id."""

    @abstractmethod
    def find_by_name(self, name: str) -> TableMaintenancePreset | None:
        """Return the preset with exactly this name, or None."""
