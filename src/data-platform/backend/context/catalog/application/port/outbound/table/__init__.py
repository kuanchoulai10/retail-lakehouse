"""Outbound ports for the table group."""

from __future__ import annotations

from context.catalog.application.domain.model.namespace import NamespaceId
from context.catalog.application.domain.model.table import (
    NullOrder,
    PartitionField,
    PartitionSpec,
    SchemaField,
    Snapshot,
    SortDirection,
    SortField,
    SortOrder,
    Table,
    TableId,
    TableSchema,
    TableSummary,
)
from context.catalog.application.port.outbound.table.tables_repo import TablesRepo

__all__ = [
    "NamespaceId",
    "NullOrder",
    "PartitionField",
    "PartitionSpec",
    "SchemaField",
    "Snapshot",
    "SortDirection",
    "SortField",
    "SortOrder",
    "Table",
    "TableId",
    "TableSchema",
    "TableSummary",
    "TablesRepo",
]
