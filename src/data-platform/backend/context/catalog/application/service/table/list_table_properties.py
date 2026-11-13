"""Define the ListTablePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.table import (
    ListTablePropertiesUseCase,
    ListTablePropertiesUseCaseInput,
    ListTablePropertiesUseCaseOutput,
    ListTablePropertiesUseCaseOutputItem,
)
from context.catalog.application.service.table.load_table_and_catalog import load_table_and_catalog
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts
from context.catalog.application.service.table.table_property_output_fields import (
    table_property_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo
    from context.catalog.application.port.outbound.table import TablesRepo


class ListTablePropertiesService(ListTablePropertiesUseCase):
    """List every property of a table next to its default, Iceberg's or the catalog's."""

    def __init__(self, tables_repo: TablesRepo, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repos: the table holds the values, its catalog the table defaults."""
        self._tables_repo = tables_repo
        self._catalogs_repo = catalogs_repo

    def execute(self, request: ListTablePropertiesUseCaseInput) -> ListTablePropertiesUseCaseOutput:
        """Return the resolved properties, or raise NotFoundError for an unknown table or catalog."""
        table_id = table_id_from_parts(request.catalog, request.namespace, request.name)
        table, catalog = load_table_and_catalog(self._tables_repo, self._catalogs_repo, table_id)
        fields = table_property_output_fields(table, catalog)
        return ListTablePropertiesUseCaseOutput(
            uuid=fields["uuid"],
            iceberg_version=fields["iceberg_version"],
            items=[ListTablePropertiesUseCaseOutputItem(**item) for item in fields["items"]],
        )
