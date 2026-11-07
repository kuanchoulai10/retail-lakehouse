"""Define the FakeReadTableMetadataGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetadataGateway,
    TableMetadata,
    TableMetadataRef,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGatewayListInput,
        TableCommitPage,
        TableDescription,
        TableMetadataObservation,
        TableStorageMeasure,
    )


class FakeReadTableMetadataGateway(ReadTableMetadataGateway):
    """Serve tables and observations registered by the test, recording calls."""

    def __init__(self) -> None:
        """Start with an empty catalog."""
        self.tables: dict[tuple[str, str, str], str] = {}
        self.observations: dict[tuple[str, str, str], TableMetadataObservation] = {}
        self.descriptions: dict[tuple[str, str, str], TableDescription] = {}
        self.commit_pages: dict[tuple[str, str, str], TableCommitPage] = {}
        self.storage_measures: dict[tuple[str, str, str], TableStorageMeasure] = {}
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
        input: ReadTableMetadataGatewayListInput,  # noqa: A002
    ) -> list[TableMetadataRef]:
        """List registered tables of the catalog."""
        self.calls.append(("list_tables", input))
        return [
            TableMetadataRef(c, n, t)
            for (c, n, t) in sorted(self.tables)
            if c == input.catalog and input.namespace in (None, n)
        ]

    def load_table(self, ref: TableMetadataRef) -> TableMetadata | None:
        """Return the registered table or None."""
        self.calls.append(("load_table", ref))
        uuid = self.tables.get((ref.catalog, ref.namespace, ref.table))
        if uuid is None:
            return None
        return TableMetadata(ref.catalog, ref.namespace, ref.table, uuid)

    def observe_table(self, ref: TableMetadataRef) -> TableMetadataObservation | None:
        """Return the registered observation or None."""
        self.calls.append(("observe_table", ref))
        return self.observations.get((ref.catalog, ref.namespace, ref.table))

    def describe_table(self, ref: TableMetadataRef) -> TableDescription | None:
        """Return the registered description or None."""
        self.calls.append(("describe_table", ref))
        return self.descriptions.get((ref.catalog, ref.namespace, ref.table))

    def list_commits(
        self, ref: TableMetadataRef, since: str | None, limit: int
    ) -> TableCommitPage | None:
        """Return the registered commit page or None."""
        self.calls.append(("list_commits", (ref, since, limit)))
        return self.commit_pages.get((ref.catalog, ref.namespace, ref.table))

    def measure_storage(self, ref: TableMetadataRef) -> TableStorageMeasure | None:
        """Return the registered storage measure or None."""
        self.calls.append(("measure_storage", ref))
        return self.storage_measures.get((ref.catalog, ref.namespace, ref.table))
