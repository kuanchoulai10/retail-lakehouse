"""Web adapter for the table_maintenance_run group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_run.dto import (
    ForwardTableMaintenanceResultApiRequest,
    ForwardTableMaintenanceResultApiResponse,
    PlatformSettingApiResponse,
    PlatformSettingsApiResponse,
    PlatformSettingsGroupApiResponse,
    TableMaintenanceRunApiResponse,
    TableMaintenanceRunAttemptApiResponse,
    TableMaintenanceRunFilterApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run.platform_settings_router import (
    platform_settings_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run.router import (
    router,
)

__all__ = [
    "PlatformSettingApiResponse",
    "PlatformSettingsApiResponse",
    "PlatformSettingsGroupApiResponse",
    "ForwardTableMaintenanceResultApiRequest",
    "ForwardTableMaintenanceResultApiResponse",
    "TableMaintenanceRunApiResponse",
    "TableMaintenanceRunAttemptApiResponse",
    "TableMaintenanceRunFilterApiResponse",
    "platform_settings_router",
    "router",
]
