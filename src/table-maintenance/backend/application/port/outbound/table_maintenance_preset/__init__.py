"""Outbound ports for the table_maintenance_preset group."""

from __future__ import annotations

from application.domain.model.table_maintenance_preset import TableMaintenancePreset
from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
    TableMaintenancePresetsRepo,
)

__all__ = [
    "TableMaintenancePreset",
    "TableMaintenancePresetsRepo",
]
