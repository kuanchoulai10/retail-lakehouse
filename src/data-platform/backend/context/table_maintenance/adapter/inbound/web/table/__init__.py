"""Web adapter for the table group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table.dto import (
    ExcludeTableApiRequest,
    IncludeTableApiRequest,
    TableApiResponse,
    TableCommitApiResponse,
    TableCommitsApiResponse,
    TableHealthApiResponse,
    TableHealthOperationApiResponse,
    TableStorageApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    UpdateTableSettingsApiRequest,
)
from context.table_maintenance.adapter.inbound.web.table.router import router

__all__ = [
    "ExcludeTableApiRequest",
    "IncludeTableApiRequest",
    "TableApiResponse",
    "TableCommitApiResponse",
    "TableCommitsApiResponse",
    "TableHealthApiResponse",
    "TableHealthOperationApiResponse",
    "TableStorageApiResponse",
    "TriggerTableMaintenanceApiRequest",
    "TriggerTableMaintenanceApiResponse",
    "UpdateTableSettingsApiRequest",
    "router",
]
