"""Define the ReadTableMetadataPyIcebergGateway."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from pyiceberg.exceptions import ForbiddenError, NoSuchNamespaceError, NoSuchTableError, RESTError, UnauthorizedError

from context.table_maintenance.adapter.outbound.table.pyiceberg.commit_page_mapper import (
    commit_page_from_table,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg.observation_mapper import (
    observation_from_table,
)
from context.table_maintenance.adapter.outbound.table.pyiceberg.table_metadata_mapper import (
    table_metadata_from_table,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    ReadTableMetadataGateway,
    ReadTableMetadataGatewayListInput,
    TableCommitPage,
    TableCommitSelection,
    TableMetadata,
    TableMetadataObservation,
    TableMetadataRef,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table


class ReadTableMetadataPyIcebergGateway(ReadTableMetadataGateway):
    """Read Iceberg metadata through PyIceberg, one catalog per Polaris catalog.

    Only "table or namespace does not exist" is mapped to None or an empty
    list. A catalog that cannot be opened because the server rejects its name
    (a bare RESTError, such as Polaris answering 404 for an unknown
    warehouse) raises CatalogNotFoundError. A refusal of the credential
    (ForbiddenError or UnauthorizedError) while opening, listing or loading
    raises CatalogAccessDeniedError. Every other failure, including server
    and availability errors, propagates, so a failing catalog can never look
    like an empty catalog.
    """

    def __init__(self, catalog_factory: Callable[[str], Catalog]) -> None:
        """Keep the factory that opens the PyIceberg catalog for a Polaris catalog name."""
        self._catalog_factory = catalog_factory

    def catalog_exists(self, catalog: str) -> bool:
        """Return whether the catalog opens; one the server rejects by name does not exist."""
        try:
            self._open(catalog)
        except CatalogNotFoundError:
            return False
        return True

    def namespace_exists(self, catalog: str, namespace: str) -> bool:
        """Return whether the dot-joined namespace exists, asking PyIceberg for its levels."""
        opened = self._open(catalog)
        with _refusal_is_access_denied(catalog):
            return opened.namespace_exists(tuple(namespace.split(".")))

    def list_tables(
        self,
        input: ReadTableMetadataGatewayListInput,  # noqa: A002
    ) -> list[TableMetadataRef]:
        """List the tables of one namespace, or walk every namespace when none is given, sorted by name."""
        catalog = self._open(input.catalog)
        with _refusal_is_access_denied(input.catalog):
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
        """Return the table with its uuid and newest commit, or None when the table or namespace does not exist."""
        table = self._load(ref)
        if table is None:
            return None
        return table_metadata_from_table(ref, table)

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

    def _open(self, name: str) -> Catalog:
        try:
            with _refusal_is_access_denied(name):
                return self._catalog_factory(name)
        except RESTError as exc:
            if type(exc) is not RESTError:
                raise
            raise CatalogNotFoundError(name) from exc

    def _load(self, ref: TableMetadataRef) -> Table | None:
        catalog = self._open(ref.catalog)
        identifier = (*ref.namespace.split("."), ref.table)
        try:
            with _refusal_is_access_denied(ref.catalog):
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


@contextmanager
def _refusal_is_access_denied(catalog: str) -> Iterator[None]:
    """Raise CatalogAccessDeniedError for a credential the server refuses on ``catalog``."""
    try:
        yield
    except (ForbiddenError, UnauthorizedError) as exc:
        raise CatalogAccessDeniedError(catalog) from exc
