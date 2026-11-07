"""Outbound ports for the generic table group."""

from __future__ import annotations

from context.catalog.application.domain.model.generic_table import GenericTable, GenericTableId
from context.catalog.application.domain.model.namespace import NamespaceId
from context.catalog.application.port.outbound.generic_table.generic_tables_repo import GenericTablesRepo

__all__ = [
    "GenericTable",
    "GenericTableId",
    "GenericTablesRepo",
    "NamespaceId",
]
