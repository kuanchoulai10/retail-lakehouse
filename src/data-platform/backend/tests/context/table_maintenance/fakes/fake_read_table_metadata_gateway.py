"""Define the FakeReadTableMetadataGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    ReadTableMetadataGateway,
    TableMetadata,
    TableMetadataRef,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGatewayListInput,
        TableCommitPage,
        TableCommitSelection,
        TableMetadataObservation,
    )

type _TableKey = tuple[str, str, str]


class FakeReadTableMetadataGateway(ReadTableMetadataGateway):
    """Serve tables and observations registered by the test, recording calls.

    Catalogs and namespaces exist as PyIceberg's do: adding a table creates its catalog and every
    level of its namespace, and dropping the table leaves them. ``list_tables`` of a catalog never
    registered answers no tables (as before this fake knew catalogs); a catalog removed with
    ``drop_catalog`` raises CatalogNotFoundError on every read. A catalog the test ``deny``s
    raises CatalogAccessDeniedError on every read, and a table it ``deny_table``s on loading.
    """

    def __init__(self) -> None:
        """Start with an empty catalog."""
        self.tables: dict[_TableKey, str] = {}
        self.last_commits: dict[_TableKey, str] = {}
        self.observations: dict[_TableKey, TableMetadataObservation] = {}
        self.commit_pages: dict[_TableKey, TableCommitPage] = {}
        self.calls: list[tuple[str, object]] = []
        self.catalogs: set[str] = set()
        self.namespaces: set[tuple[str, str]] = set()
        self.dropped_catalogs: set[str] = set()
        self.denied_catalogs: set[str] = set()
        self.denied_tables: set[_TableKey] = set()

    def add_catalog(self, name: str) -> None:
        """Register a catalog that holds nothing yet."""
        self.catalogs.add(name)
        self.dropped_catalogs.discard(name)

    def add_namespace(self, catalog: str, namespace: str) -> None:
        """Register a dot-joined namespace and every level above it, and their catalog."""
        self.add_catalog(catalog)
        levels = namespace.split(".")
        self.namespaces.update((catalog, ".".join(levels[:depth])) for depth in range(1, len(levels) + 1))

    def add_table(
        self,
        catalog: str,
        namespace: str,
        table: str,
        table_uuid: str,
        *,
        last_committed_at: str | None = None,
    ) -> None:
        """Register a table, with the ISO time of its newest commit when it has one."""
        self.add_namespace(catalog, namespace)
        self.tables[(catalog, namespace, table)] = table_uuid
        if last_committed_at is None:
            self.last_commits.pop((catalog, namespace, table), None)
        else:
            self.last_commits[(catalog, namespace, table)] = last_committed_at

    def drop_table(self, catalog: str, namespace: str, table: str) -> None:
        """Remove a registered table; its namespace and catalog stay."""
        self.tables.pop((catalog, namespace, table), None)

    def rename(self, table_uuid: str, *, namespace: str | None = None, table: str | None = None) -> None:
        """Move the table with ``table_uuid`` to another namespace or name in its catalog, keeping its uuid."""
        (old,) = [key for key, uuid in self.tables.items() if uuid == table_uuid]
        catalog, old_namespace, old_table = old
        last_commit = self.last_commits.pop(old, None)
        del self.tables[old]
        self.add_table(
            catalog,
            old_namespace if namespace is None else namespace,
            old_table if table is None else table,
            table_uuid,
            last_committed_at=last_commit,
        )

    def drop_namespace(self, catalog: str, namespace: str) -> None:
        """Remove a namespace with its child namespaces and their tables."""
        self.namespaces = {(c, n) for c, n in self.namespaces if not (c == catalog and _within(n, namespace))}
        for key in [k for k in self.tables if k[0] == catalog and _within(k[1], namespace)]:
            del self.tables[key]

    def drop_catalog(self, name: str) -> None:
        """Remove a catalog with everything in it; every read of it then raises CatalogNotFoundError."""
        self.catalogs.discard(name)
        self.namespaces = {(c, n) for c, n in self.namespaces if c != name}
        for key in [k for k in self.tables if k[0] == name]:
            del self.tables[key]
        self.dropped_catalogs.add(name)

    def deny(self, catalog: str) -> None:
        """Refuse the credential on every read of ``catalog``."""
        self.denied_catalogs.add(catalog)

    def allow(self, catalog: str) -> None:
        """Read ``catalog`` again after a ``deny``."""
        self.denied_catalogs.discard(catalog)

    def deny_table(self, catalog: str, namespace: str, table: str) -> None:
        """Refuse the credential on loading, observing or listing the commits of one table."""
        self.denied_tables.add((catalog, namespace, table))

    def catalog_exists(self, catalog: str) -> bool:
        """Return whether the catalog is registered, raising for a denied one."""
        self.calls.append(("catalog_exists", catalog))
        self._check_access(catalog)
        return catalog in self.catalogs

    def namespace_exists(self, catalog: str, namespace: str) -> bool:
        """Return whether the namespace is registered, raising for a denied or an unknown catalog."""
        self.calls.append(("namespace_exists", (catalog, namespace)))
        self._check_access(catalog)
        if catalog not in self.catalogs:
            raise CatalogNotFoundError(catalog)
        return (catalog, namespace) in self.namespaces

    def list_tables(
        self,
        input: ReadTableMetadataGatewayListInput,  # noqa: A002
    ) -> list[TableMetadataRef]:
        """List registered tables of the catalog."""
        self.calls.append(("list_tables", input))
        self._check_readable(input.catalog)
        return [
            TableMetadataRef(c, n, t)
            for (c, n, t) in sorted(self.tables)
            if c == input.catalog and input.namespace in (None, n)
        ]

    def load_table(self, ref: TableMetadataRef) -> TableMetadata | None:
        """Return the registered table or None."""
        self.calls.append(("load_table", ref))
        self._check_table_readable(ref)
        uuid = self.tables.get((ref.catalog, ref.namespace, ref.table))
        if uuid is None:
            return None
        last_commit = self.last_commits.get((ref.catalog, ref.namespace, ref.table))
        return TableMetadata(ref.catalog, ref.namespace, ref.table, uuid, last_committed_at=last_commit)

    def observe_table(self, ref: TableMetadataRef) -> TableMetadataObservation | None:
        """Return the registered observation or None."""
        self.calls.append(("observe_table", ref))
        self._check_table_readable(ref)
        return self.observations.get((ref.catalog, ref.namespace, ref.table))

    def list_commits(
        self,
        ref: TableMetadataRef,
        selection: TableCommitSelection,
    ) -> TableCommitPage | None:
        """Return the registered commit page or None."""
        self.calls.append(("list_commits", (ref, selection)))
        self._check_table_readable(ref)
        return self.commit_pages.get((ref.catalog, ref.namespace, ref.table))

    def _check_access(self, catalog: str) -> None:
        if catalog in self.denied_catalogs:
            raise CatalogAccessDeniedError(catalog)

    def _check_readable(self, catalog: str) -> None:
        self._check_access(catalog)
        if catalog in self.dropped_catalogs:
            raise CatalogNotFoundError(catalog)

    def _check_table_readable(self, ref: TableMetadataRef) -> None:
        self._check_readable(ref.catalog)
        if (ref.catalog, ref.namespace, ref.table) in self.denied_tables:
            raise CatalogAccessDeniedError(ref.catalog)


def _within(namespace: str, parent: str) -> bool:
    return namespace == parent or namespace.startswith(f"{parent}.")
