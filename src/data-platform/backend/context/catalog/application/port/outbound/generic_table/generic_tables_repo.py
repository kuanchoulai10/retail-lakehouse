"""Define the GenericTablesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.catalog.application.domain.model.generic_table import GenericTable

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.application.domain.model.generic_table import GenericTableId
    from context.catalog.application.domain.model.namespace import NamespaceId


class GenericTablesRepo(Repository[GenericTable]):
    """Load and save GenericTable aggregates in the catalog service, which holds them.

    ``create`` returns the generic table as the catalog saved it; it raises ConflictError when
    the name is taken and NotFoundError when the namespace does not exist. ``get`` returns None
    for an unknown generic table. ``list_all`` returns every generic table of every catalog.
    """

    @abstractmethod
    def get(self, entity_id: EntityId | ModelEntityId) -> GenericTable | None:
        """Return the generic table with the given id, or None when there is none."""

    @abstractmethod
    def list_in(self, namespace: NamespaceId) -> list[GenericTableId]:
        """Return the ids of the generic tables directly in ``namespace``; NotFoundError for an unknown namespace."""

    @abstractmethod
    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Drop the generic table from the catalog; NotFoundError for an unknown one."""
