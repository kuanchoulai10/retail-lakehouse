"""Define the ReadTableMetadataPyIcebergGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError

from context.table_maintenance.adapter.outbound.table.pyiceberg.commit_page_mapper import (
    commit_page_from_table,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg.observation_mapper import (
    observation_from_table,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg.storage_measure_mapper import (
    storage_measure_from_table,
)
from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetadataGateway,
    ReadTableMetadataGatewayListInput,
    TableCommitPage,
    TableCommitSelection,
    TableMetadata,
    TableMetadataObservation,
    TableMetadataRef,
    TableStorageMeasure,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table


class ReadTableMetadataPyIcebergGateway(ReadTableMetadataGateway):
    """Read Iceberg metadata through PyIceberg, one catalog per Polaris catalog.

    Only "table or namespace does not exist" is mapped to None or an empty
    list. Every other failure propagates, so a transient catalog error can
    never look like an empty catalog.
    """

    def __init__(self, catalog_factory: Callable[[str], Catalog]) -> None:
        """Keep the factory that opens the PyIceberg catalog for a Polaris catalog name."""
        self._catalog_factory = catalog_factory

    def list_tables(
        self,
        input: ReadTableMetadataGatewayListInput,  # noqa: A002
    ) -> list[TableMetadataRef]:
        """List the tables of one namespace, or walk every namespace when none is given, sorted by name."""
        catalog = self._catalog_factory(input.catalog)
        if input.namespace is not None:
            return self._tables_of(catalog, input.catalog, tuple(input.namespace.split(".")))
        refs: list[TableMetadataRef] = []
        pending: list[tuple[str, ...]] = [tuple(n) for n in catalog.list_namespaces()]
        while pending:
            namespace = pending.pop(0)
            refs.extend(self._tables_of(catalog, input.catalog, namespace))
            try:
                pending.extend(tuple(n) for n in catalog.list_namespaces(namespace))
            except NoSuchNamespaceError:
                continue
        return sorted(refs, key=lambda r: (r.namespace, r.table))

    def load_table(self, ref: TableMetadataRef) -> TableMetadata | None:
        """Return the table with its uuid, or None when the table or namespace does not exist."""
        table = self._load(ref)
        if table is None:
            return None
        return TableMetadata(
            catalog=ref.catalog,
            namespace=ref.namespace,
            table=ref.table,
            table_uuid=str(table.metadata.table_uuid),
        )

    def observe_table(self, ref: TableMetadataRef) -> TableMetadataObservation | None:
        """Return the table's statistics, or None when the table or namespace does not exist."""
        table = self._load(ref)
        if table is None:
            return None
        return observation_from_table(table)

    def list_commits(
        self,
        ref: TableMetadataRef,
        selection: TableCommitSelection,
    ) -> TableCommitPage | None:
        """Return up to ``selection.limit`` of the selected commits, newest first, or None when the table is gone."""
        table = self._load(ref)
        if table is None:
            return None
        return commit_page_from_table(table, selection)

    def measure_storage(self, ref: TableMetadataRef) -> TableStorageMeasure | None:
        """Return the table's current and referenced storage, or None when the table does not exist."""
        table = self._load(ref)
        if table is None:
            return None
        return storage_measure_from_table(table)

    def _load(self, ref: TableMetadataRef) -> Table | None:
        catalog = self._catalog_factory(ref.catalog)
        identifier = (*ref.namespace.split("."), ref.table)
        try:
            return catalog.load_table(identifier)
        except NoSuchTableError:
            return None

    @staticmethod
    def _tables_of(catalog: Catalog, catalog_name: str, namespace: tuple[str, ...]) -> list[TableMetadataRef]:
        try:
            identifiers = catalog.list_tables(namespace)
        except NoSuchNamespaceError:
            return []
        return [
            TableMetadataRef(
                catalog=catalog_name,
                namespace=".".join(identifier[:-1]),
                table=identifier[-1],
            )
            for identifier in identifiers
        ]
