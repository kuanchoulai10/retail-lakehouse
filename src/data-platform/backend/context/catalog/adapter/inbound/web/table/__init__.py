"""Web adapter for the table group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.table.dto import (
    CreateTableApiRequest,
    PartitionFieldApiRequest,
    PartitionFieldApiResponse,
    PartitionSpecApiResponse,
    RenameTableApiRequest,
    SchemaFieldApiRequest,
    SchemaFieldApiResponse,
    SnapshotApiResponse,
    SortFieldApiResponse,
    SortOrderApiResponse,
    TableApiResponse,
    TableIdentifierApiResponse,
    TableSchemaApiResponse,
    TableSummaryApiResponse,
    UpdateTablePropertiesApiRequest,
)
from context.catalog.adapter.inbound.web.table.router import router

__all__ = [
    "CreateTableApiRequest",
    "PartitionFieldApiRequest",
    "PartitionFieldApiResponse",
    "PartitionSpecApiResponse",
    "RenameTableApiRequest",
    "SchemaFieldApiRequest",
    "SchemaFieldApiResponse",
    "SnapshotApiResponse",
    "SortFieldApiResponse",
    "SortOrderApiResponse",
    "TableApiResponse",
    "TableIdentifierApiResponse",
    "TableSchemaApiResponse",
    "TableSummaryApiResponse",
    "UpdateTablePropertiesApiRequest",
    "router",
]
