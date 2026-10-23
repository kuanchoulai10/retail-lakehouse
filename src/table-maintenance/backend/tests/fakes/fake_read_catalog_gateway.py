"""Define the FakeReadCatalogGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.catalog.read_catalog import (
    ReadCatalogGateway,
    ReadCatalogGatewayTable,
    ReadCatalogGatewayTableRef,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog import (
        ReadCatalogGatewayListInput,
        ReadCatalogGatewayObservation,
    )


class FakeReadCatalogGateway(ReadCatalogGateway):
    """Serve tables and observations registered by the test, recording calls."""

    def __init__(self) -> None:
        """Start with an empty catalog."""
        self.tables: dict[tuple[str, str, str], str] = {}
        self.observations: dict[
            tuple[str, str, str], ReadCatalogGatewayObservation
        ] = {}
        self.calls: list[tuple[str, object]] = []

    def add_table(
        self, catalog: str, namespace: str, table: str, table_uuid: str
    ) -> None:
        """Register a table."""
        self.tables[(catalog, namespace, table)] = table_uuid

    def drop_table(self, catalog: str, namespace: str, table: str) -> None:
        """Remove a registered table."""
        self.tables.pop((catalog, namespace, table), None)

    def list_tables(
        self,
        input: ReadCatalogGatewayListInput,  # noqa: A002
    ) -> list[ReadCatalogGatewayTableRef]:
        """List registered tables of the catalog."""
        self.calls.append(("list_tables", input))
        return [
            ReadCatalogGatewayTableRef(c, n, t)
            for (c, n, t) in sorted(self.tables)
            if c == input.catalog and input.namespace in (None, n)
        ]

    def load_table(
        self, ref: ReadCatalogGatewayTableRef
    ) -> ReadCatalogGatewayTable | None:
        """Return the registered table or None."""
        self.calls.append(("load_table", ref))
        uuid = self.tables.get((ref.catalog, ref.namespace, ref.table))
        if uuid is None:
            return None
        return ReadCatalogGatewayTable(ref.catalog, ref.namespace, ref.table, uuid)

    def observe_table(
        self, ref: ReadCatalogGatewayTableRef
    ) -> ReadCatalogGatewayObservation | None:
        """Return the registered observation or None."""
        self.calls.append(("observe_table", ref))
        return self.observations.get((ref.catalog, ref.namespace, ref.table))
