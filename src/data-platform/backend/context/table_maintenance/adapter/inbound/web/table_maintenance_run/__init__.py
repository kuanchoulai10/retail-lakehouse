"""Web adapter for the table_maintenance_run group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_run.dto import (
    PlatformSettingApiResponse,
    PlatformSettingsApiResponse,
    PlatformSettingsGroupApiResponse,
    ProcessTableMaintenanceCallbackApiRequest,
    ProcessTableMaintenanceCallbackApiResponse,
    TableMaintenanceRunApiResponse,
    TableMaintenanceRunAttemptApiResponse,
    TableMaintenanceRunOperationApiResponse,
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
    "ProcessTableMaintenanceCallbackApiRequest",
    "ProcessTableMaintenanceCallbackApiResponse",
    "TableMaintenanceRunApiResponse",
    "TableMaintenanceRunAttemptApiResponse",
    "TableMaintenanceRunOperationApiResponse",
    "platform_settings_router",
    "router",
]
