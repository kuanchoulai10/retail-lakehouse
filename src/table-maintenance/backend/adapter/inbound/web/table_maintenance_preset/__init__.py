"""Web adapter for the table_maintenance_preset group."""

from __future__ import annotations

from adapter.inbound.web.table_maintenance_preset.dto import (
    CreateTableMaintenancePresetApiRequest,
    TableMaintenancePresetApiResponse,
    UpdateTableMaintenancePresetApiRequest,
)
from adapter.inbound.web.table_maintenance_preset.router import router

__all__ = [
    "CreateTableMaintenancePresetApiRequest",
    "TableMaintenancePresetApiResponse",
    "UpdateTableMaintenancePresetApiRequest",
    "router",
]
