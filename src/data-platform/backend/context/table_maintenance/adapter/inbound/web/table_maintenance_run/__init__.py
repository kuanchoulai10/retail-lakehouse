"""Web adapter for the table_maintenance_run group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_run.dto import (
    ProcessTableMaintenanceCallbackApiRequest,
    ProcessTableMaintenanceCallbackApiResponse,
    TableMaintenanceRunApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run.router import (
    router,
)

__all__ = [
    "ProcessTableMaintenanceCallbackApiRequest",
    "ProcessTableMaintenanceCallbackApiResponse",
    "TableMaintenanceRunApiResponse",
    "router",
]
