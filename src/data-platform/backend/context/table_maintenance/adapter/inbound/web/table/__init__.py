"""Web adapter for the table group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table.dto import (
    SetTablePriorityApiRequest,
    TableApiResponse,
    TableCommitApiResponse,
    TableCommitsApiResponse,
    TableCurrentMetricsApiResponse,
    TableMetricTrendPointApiResponse,
    TableMetricTrendsApiResponse,
    TableMetricValuesApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    TriggerTableReconciliationApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table.effective_policies_dto import (
    DiscoveryEffectivePolicyApiResponse,
    EffectivePoliciesApiResponse,
    MaintenanceEffectivePolicyApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table.effective_policies_router import (
    effective_policies_router,
)
from context.table_maintenance.adapter.inbound.web.table.router import router
from context.table_maintenance.adapter.inbound.web.table.table_metrics_exposition import (
    render_table_metrics_exposition,
)
from context.table_maintenance.adapter.inbound.web.table.table_metrics_router import (
    table_metrics_router,
)

__all__ = [
    "DiscoveryEffectivePolicyApiResponse",
    "EffectivePoliciesApiResponse",
    "MaintenanceEffectivePolicyApiResponse",
    "SetTablePriorityApiRequest",
    "TableApiResponse",
    "TableCommitApiResponse",
    "TableCommitsApiResponse",
    "TableCurrentMetricsApiResponse",
    "TableMetricTrendPointApiResponse",
    "TableMetricTrendsApiResponse",
    "TableMetricValuesApiResponse",
    "TriggerTableMaintenanceApiRequest",
    "TriggerTableMaintenanceApiResponse",
    "TriggerTableReconciliationApiResponse",
    "effective_policies_router",
    "render_table_metrics_exposition",
    "router",
    "table_metrics_router",
]
