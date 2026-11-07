"""Web adapter for the table group."""

from __future__ import annotations

from adapter.inbound.web.table.dto import (
    ExcludeTableApiRequest,
    IncludeTableApiRequest,
    TableApiResponse,
    TableCommitApiResponse,
    TableCommitsApiResponse,
    TableHealthApiResponse,
    TableHealthOperationApiResponse,
    TableMetadataApiResponse,
    TableStorageApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    UpdateTableSettingsApiRequest,
)
from adapter.inbound.web.table.router import router

__all__ = [
    "ExcludeTableApiRequest",
    "IncludeTableApiRequest",
    "TableApiResponse",
    "TableCommitApiResponse",
    "TableCommitsApiResponse",
    "TableHealthApiResponse",
    "TableHealthOperationApiResponse",
    "TableMetadataApiResponse",
    "TableStorageApiResponse",
    "TriggerTableMaintenanceApiRequest",
    "TriggerTableMaintenanceApiResponse",
    "UpdateTableSettingsApiRequest",
    "router",
]
