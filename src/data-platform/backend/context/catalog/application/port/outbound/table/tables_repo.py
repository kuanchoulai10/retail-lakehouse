"""Define the TablesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.catalog.application.domain.model.table import Table

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.application.domain.model.namespace import NamespaceId
    from context.catalog.application.domain.model.table import TableId


class TablesRepo(Repository[Table]):
    """Load and save Iceberg Table aggregates in the catalog service, which holds them.

    ``create`` takes a table from ``Table.define`` and returns it as the catalog saved it, with
    its uuid; it raises ConflictError when the name is taken and NotFoundError when the
    namespace does not exist. ``get`` returns None for an unknown table. ``list_all`` returns
    every table of every catalog.
    """

    @abstractmethod
    def list_in(self, namespace: NamespaceId) -> list[TableId]:
        """Return the ids of the tables directly in ``namespace``; NotFoundError for an unknown namespace."""

    @abstractmethod
    def rename(self, source: TableId, target: TableId) -> None:
        """Move ``source`` to ``target``, which may be in another namespace of the same catalog.

        Raises NotFoundError for an unknown source or target namespace, ConflictError for a taken target.
        """

    @abstractmethod
    def update_properties(
        self, entity_id: TableId, expected_uuid: str, updates: dict[str, str], removals: list[str]
    ) -> Table:
        """Set ``updates`` and remove ``removals`` on the table whose uuid is ``expected_uuid``; return it as saved.

        Raises NotFoundError for an unknown table and ConflictError when the table under this
        name is no longer the one with ``expected_uuid`` (it was dropped and created again).
        """

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Drop the table from the catalog; its data and metadata files are never purged."""
