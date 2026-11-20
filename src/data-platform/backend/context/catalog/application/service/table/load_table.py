"""Define the load_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import Table, TableId, TablesRepo


def load_table(tables_repo: TablesRepo, table_id: TableId) -> Table:
    """Return the table, or raise NotFoundError naming it, its namespace and its catalog."""
    table = tables_repo.get(table_id)
    if table is None:
        raise NotFoundError(
            f"table {table_id.name} not found in namespace {list(table_id.namespace)} of catalog {table_id.catalog}"
        )
    return table
