"""Define the NamespacesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.catalog.application.domain.model.namespace import Namespace

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.application.domain.model.catalog import CatalogId
    from context.catalog.application.domain.model.namespace import NamespaceId


class NamespacesRepo(Repository[Namespace]):
    """Load and save Namespace aggregates in the catalog service, which holds them.

    ``create`` raises ConflictError when the namespace exists and NotFoundError when its
    parent does not, and returns the namespace as saved. ``get`` returns None for an unknown
    namespace. ``list_all`` returns every namespace of every catalog.
    """

    @abstractmethod
    def get(self, entity_id: EntityId | ModelEntityId) -> Namespace | None:
        """Return the namespace with the given id, or None when there is none."""

    @abstractmethod
    def list_in(self, catalog: CatalogId, parent: tuple[str, ...]) -> list[Namespace]:
        """Return the direct children of ``parent`` (the top level when it is empty), without properties."""

    @abstractmethod
    def update_properties(self, entity_id: NamespaceId, updates: dict[str, str], removals: list[str]) -> Namespace:
        """Set ``updates``, remove ``removals`` and return the namespace as saved.

        Raises NotFoundError for an unknown namespace.
        """

    @abstractmethod
    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Delete the namespace; one that still holds content or children is refused, never emptied."""
