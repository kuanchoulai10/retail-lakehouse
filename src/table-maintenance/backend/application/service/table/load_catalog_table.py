"""Define the load_catalog_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table import TableId
from application.exceptions import NotFoundError
from application.port.outbound.table import TableMetadataRef

if TYPE_CHECKING:
    from application.domain.model.table import Table
    from application.port.outbound.table import TablesRepo


def load_catalog_table(
    tables_repo: TablesRepo, uuid: str
) -> tuple[Table, TableMetadataRef]:
    """Return the registered table and its catalog reference, or raise NotFoundError."""
    table = tables_repo.get(TableId(uuid))
    if table is None:
        raise NotFoundError(f"table {uuid} not found")
    name = table.name
    return table, TableMetadataRef(name.catalog, name.namespace, name.table)
