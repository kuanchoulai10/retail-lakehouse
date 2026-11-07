"""Define the TablesPolarisRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from context.catalog.adapter.outbound.shared.polaris import (
    iceberg_namespace_path,
    raise_for_paged_listing,
    walk_iceberg_namespaces,
)
from context.catalog.adapter.outbound.table.polaris.partition_spec_to_polaris import (
    partition_spec_to_polaris,
)
from context.catalog.adapter.outbound.table.polaris.table_from_polaris import table_from_polaris
from context.catalog.adapter.outbound.table.polaris.table_schema_to_polaris import (
    table_schema_to_polaris,
)
from context.catalog.application.exceptions import CatalogUnavailableError, NotFoundError
from context.catalog.application.port.outbound.table import NamespaceId, Table, TableId, TablesRepo

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient


def _tables_path(catalog: str, namespace: tuple[str, ...]) -> str:
    return f"{iceberg_namespace_path(catalog, namespace)}/tables"


def _table_path(table_id: TableId) -> str:
    return f"{_tables_path(table_id.catalog, table_id.namespace)}/{quote(table_id.name, safe='')}"


def _table_id(catalog: str, item: dict[str, Any]) -> TableId:
    namespace, name = item["namespace"], item["name"]
    if not isinstance(namespace, list) or not isinstance(name, str):
        raise TypeError(f"identifier {item!r} needs a namespace list and a name")
    return TableId.of(catalog, tuple(str(part) for part in namespace), name)


def _identifier(table_id: TableId) -> dict[str, Any]:
    return {"namespace": list(table_id.namespace), "name": table_id.name}


class TablesPolarisRepo(TablesRepo):
    """Load and save Iceberg tables through the Iceberg REST API of Polaris; nothing is cached.

    Every read maps the ``metadata`` of the reply (LoadTableResult or CommitTableResponse);
    the ``config`` block, which may carry storage credentials, is never read.
    """

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, entity: Table) -> Table:
        """POST the name, schema, partition spec, location and properties; return the table Polaris created.

        An unpartitioned spec and a missing location are left out, so Polaris applies its defaults.
        """
        body: dict[str, Any] = {"name": entity.id.name, "schema": table_schema_to_polaris(entity.schema)}
        if entity.partition_spec.fields:
            body["partition-spec"] = partition_spec_to_polaris(entity.partition_spec)
        if entity.location:
            body["location"] = entity.location
        body["properties"] = dict(entity.properties)
        response = self._polaris.catalog_request(
            "POST", _tables_path(entity.id.catalog, entity.id.namespace), json=body
        )
        return table_from_polaris(entity.id, response)

    def get(self, entity_id: EntityId) -> Table | None:
        """GET the table; Polaris's 404 means there is none."""
        table_id = TableId(entity_id.value)
        try:
            response = self._polaris.catalog_request("GET", _table_path(table_id))
        except NotFoundError:
            return None
        return table_from_polaris(table_id, response)

    def list_in(self, namespace: NamespaceId) -> list[TableId]:
        """GET the identifiers of the namespace's tables; a paged reply is refused."""
        response = self._polaris.catalog_request("GET", _tables_path(namespace.catalog, namespace.parts))
        try:
            body = response.json()
            identifiers = body.get("identifiers", [])
            found = [_table_id(namespace.catalog, item) for item in identifiers]
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise CatalogUnavailableError(
                f"Polaris returned the tables of namespace {list(namespace.parts)} in a form this backend "
                f"cannot read: {exc!r}"
            ) from exc
        raise_for_paged_listing(body)
        return found

    def list_all(self) -> list[Table]:
        """Walk every namespace of every catalog and load each of its tables."""
        found: list[Table] = []
        for catalog, parts in walk_iceberg_namespaces(self._polaris):
            for table_id in self.list_in(NamespaceId.of(catalog, parts)):
                table = self.get(table_id)
                if table is not None:
                    found.append(table)
        return found

    def rename(self, source: TableId, target: TableId) -> None:
        """POST the source and destination identifiers to the catalog's ``/tables/rename``."""
        self._polaris.catalog_request(
            "POST",
            f"/v1/{quote(source.catalog, safe='')}/tables/rename",
            json={"source": _identifier(source), "destination": _identifier(target)},
        )

    def update_properties(
        self, entity_id: TableId, expected_uuid: str, updates: dict[str, str], removals: list[str]
    ) -> Table:
        """Commit the change with an ``assert-table-uuid`` requirement and map the committed metadata.

        Polaris answers a failed requirement with 409, which ``raise_for_polaris`` raises as ConflictError.
        """
        changes: list[dict[str, Any]] = []
        if updates:
            changes.append({"action": "set-properties", "updates": dict(updates)})
        if removals:
            changes.append({"action": "remove-properties", "removals": list(removals)})
        response = self._polaris.catalog_request(
            "POST",
            _table_path(entity_id),
            json={"requirements": [{"type": "assert-table-uuid", "uuid": expected_uuid}], "updates": changes},
        )
        return table_from_polaris(entity_id, response)

    def delete(self, entity_id: EntityId) -> None:
        """DELETE the table with ``purgeRequested=false``, so its files stay."""
        self._polaris.catalog_request(
            "DELETE", _table_path(TableId(entity_id.value)), params={"purgeRequested": "false"}
        )
