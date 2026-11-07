"""Outbound ports for the table group."""

from __future__ import annotations

from context.catalog.application.domain.model.namespace import NamespaceId
from context.catalog.application.domain.model.table import (
    NullOrder,
    PartitionField,
    PartitionSpec,
    Snapshot,
    SortDirection,
    SortField,
    SortOrder,
    Table,
    TableId,
    TableSummary,
)
from context.catalog.application.port.outbound.shared import Schema, SchemaField
from context.catalog.application.port.outbound.table.tables_repo import TablesRepo

__all__ = [
    "NamespaceId",
    "NullOrder",
    "PartitionField",
    "PartitionSpec",
    "Schema",
    "SchemaField",
    "Snapshot",
    "SortDirection",
    "SortField",
    "SortOrder",
    "Table",
    "TableId",
    "TableSummary",
    "TablesRepo",
]
