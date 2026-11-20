"""Define the load_table_and_catalog function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.service.catalog import catalog_id_from_name
from context.catalog.application.service.table.load_table import load_table

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import Catalog, CatalogsRepo
    from context.catalog.application.port.outbound.table import Table, TableId, TablesRepo


def load_table_and_catalog(
    tables_repo: TablesRepo, catalogs_repo: CatalogsRepo, table_id: TableId
) -> tuple[Table, Catalog]:
    """Return the table and the catalog that holds it, whose table defaults apply; NotFoundError for either missing."""
    table = load_table(tables_repo, table_id)
    catalog = catalogs_repo.get(catalog_id_from_name(table_id.catalog))
    if catalog is None:
        raise NotFoundError(f"catalog {table_id.catalog} not found")
    return table, catalog
