"""Web adapter for the table group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table.dto import (
    SetTablePriorityApiRequest,
    TableApiResponse,
    TableCommitApiResponse,
    TableCommitsApiResponse,
    TableHealthApiResponse,
    TableHealthOperationApiResponse,
    TableStorageApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    TriggerTableReconciliationApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table.router import router

__all__ = [
    "SetTablePriorityApiRequest",
    "TableApiResponse",
    "TableCommitApiResponse",
    "TableCommitsApiResponse",
    "TableHealthApiResponse",
    "TableHealthOperationApiResponse",
    "TableStorageApiResponse",
    "TriggerTableMaintenanceApiRequest",
    "TriggerTableMaintenanceApiResponse",
    "TriggerTableReconciliationApiResponse",
    "router",
]
