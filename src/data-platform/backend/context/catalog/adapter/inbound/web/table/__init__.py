"""Web adapter for the table group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.table.change_counts_response import change_counts_response
from context.catalog.adapter.inbound.web.table.dto import (
    CatalogTableApiResponse,
    CatalogTablePartitionSpecComparisonApiResponse,
    CatalogTablePartitionSpecVersionApiResponse,
    CatalogTablePartitionSpecVersionsApiResponse,
    CatalogTablePropertiesApiResponse,
    CatalogTablePropertyApiResponse,
    CatalogTableSchemaComparisonApiResponse,
    CatalogTableSchemaVersionApiResponse,
    CatalogTableSchemaVersionsApiResponse,
    CreateTableApiRequest,
    PartitionChangeCountsApiResponse,
    PartitionFieldApiRequest,
    PartitionFieldApiResponse,
    PartitionFieldComparisonApiResponse,
    PartitionSpecApiResponse,
    RenameTableApiRequest,
    ResetTablePropertiesApiRequest,
    SchemaChangeCountsApiResponse,
    SchemaFieldApiRequest,
    SchemaFieldComparisonApiResponse,
    SnapshotApiResponse,
    SortFieldApiResponse,
    SortOrderApiResponse,
    TableIdentifierApiResponse,
    TableSummaryApiResponse,
    UpdateTablePropertiesApiRequest,
)
from context.catalog.adapter.inbound.web.table.partition_field_comparison_response import (
    partition_field_comparison_response,
)
from context.catalog.adapter.inbound.web.table.router import router

__all__ = [
    "CreateTableApiRequest",
    "PartitionFieldApiRequest",
    "PartitionFieldApiResponse",
    "PartitionSpecApiResponse",
    "RenameTableApiRequest",
    "ResetTablePropertiesApiRequest",
    "SchemaFieldApiRequest",
    "SnapshotApiResponse",
    "SortFieldApiResponse",
    "SortOrderApiResponse",
    "CatalogTableApiResponse",
    "CatalogTablePropertiesApiResponse",
    "CatalogTablePropertyApiResponse",
    "CatalogTablePartitionSpecComparisonApiResponse",
    "CatalogTablePartitionSpecVersionApiResponse",
    "CatalogTablePartitionSpecVersionsApiResponse",
    "CatalogTableSchemaComparisonApiResponse",
    "CatalogTableSchemaVersionApiResponse",
    "CatalogTableSchemaVersionsApiResponse",
    "PartitionChangeCountsApiResponse",
    "PartitionFieldComparisonApiResponse",
    "SchemaChangeCountsApiResponse",
    "SchemaFieldComparisonApiResponse",
    "TableIdentifierApiResponse",
    "TableSummaryApiResponse",
    "UpdateTablePropertiesApiRequest",
    "change_counts_response",
    "partition_field_comparison_response",
    "router",
]
