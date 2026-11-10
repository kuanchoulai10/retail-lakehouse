"""Define the GenericTablesPolarisRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from context.catalog.adapter.outbound.generic_table.polaris.generic_table_from_polaris import (
    generic_table_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris import (
    iceberg_namespace_path,
    listed_identifiers,
    walk_iceberg_namespaces,
)
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.outbound.generic_table import (
    GenericTable,
    GenericTableId,
    GenericTablesRepo,
    NamespaceId,
)

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient

_POLARIS_API = "/polaris"


def _tables_path(catalog: str, namespace: tuple[str, ...]) -> str:
    return f"{_POLARIS_API}{iceberg_namespace_path(catalog, namespace)}/generic-tables"


def _table_path(table_id: GenericTableId) -> str:
    return f"{_tables_path(table_id.catalog, table_id.namespace)}/{quote(table_id.name, safe='')}"


class GenericTablesPolarisRepo(GenericTablesRepo):
    """Load and save generic tables through the Polaris generic tables API; nothing is cached.

    Paths sit under ``/polaris/v1/{catalog}/namespaces/{namespace}/generic-tables``, the Polaris
    API, not under the Iceberg REST ``/v1`` that tables and views use.
    """

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, entity: GenericTable) -> GenericTable:
        """POST the name, format, base location, doc and properties; return the table Polaris created.

        An absent base location or doc is left out of the body.
        """
        body: dict[str, Any] = {"name": entity.id.name, "format": entity.format}
        if entity.base_location:
            body["base-location"] = entity.base_location
        if entity.doc:
            body["doc"] = entity.doc
        body["properties"] = dict(entity.properties)
        response = self._polaris.catalog_request(
            "POST", _tables_path(entity.id.catalog, entity.id.namespace), json=body
        )
        return generic_table_from_polaris(entity.id, response)

    def get(self, entity_id: EntityId | ModelEntityId) -> GenericTable | None:
        """GET the generic table; Polaris's 404 means there is none."""
        table_id = GenericTableId(entity_id.value)
        try:
            response = self._polaris.catalog_request("GET", _table_path(table_id))
        except NotFoundError:
            return None
        return generic_table_from_polaris(table_id, response)

    def list_in(self, namespace: NamespaceId) -> list[GenericTableId]:
        """GET the identifiers of the namespace's generic tables; a paged reply is refused."""
        response = self._polaris.catalog_request("GET", _tables_path(namespace.catalog, namespace.parts))
        found = listed_identifiers(response, f"the generic tables of namespace {list(namespace.parts)}")
        return [GenericTableId.of(namespace.catalog, parts, name) for parts, name in found]

    def list_all(self) -> list[GenericTable]:
        """Walk every namespace of every catalog and load each of its generic tables."""
        found: list[GenericTable] = []
        for catalog, parts in walk_iceberg_namespaces(self._polaris):
            for table_id in self.list_in(NamespaceId.of(catalog, parts)):
                table = self.get(table_id)
                if table is not None:
                    found.append(table)
        return found

    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """DELETE the generic table."""
        self._polaris.catalog_request("DELETE", _table_path(GenericTableId(entity_id.value)))
