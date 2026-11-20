"""Web adapter for the table group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table.dto import (
    SetTablePriorityApiRequest,
    TableApiResponse,
    TableCommitApiResponse,
    TableCommitsApiResponse,
    TableCurrentMetricsApiResponse,
    TableMetricValuesApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    TriggerTableReconciliationApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table.router import router
from context.table_maintenance.adapter.inbound.web.table.table_metrics_exposition import (
    render_table_metrics_exposition,
)
from context.table_maintenance.adapter.inbound.web.table.table_metrics_router import (
    table_metrics_router,
)

__all__ = [
    "SetTablePriorityApiRequest",
    "TableApiResponse",
    "TableCommitApiResponse",
    "TableCommitsApiResponse",
    "TableCurrentMetricsApiResponse",
    "TableMetricValuesApiResponse",
    "TriggerTableMaintenanceApiRequest",
    "TriggerTableMaintenanceApiResponse",
    "TriggerTableReconciliationApiResponse",
    "render_table_metrics_exposition",
    "router",
    "table_metrics_router",
]
