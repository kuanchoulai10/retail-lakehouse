"""Define the CatalogsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.catalog.application.domain.model.catalog import Catalog

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId


class CatalogsRepo(Repository[Catalog]):
    """Load and save Catalog aggregates in the catalog service, which holds them.

    ``create`` raises ConflictError when the name is taken, and returns the catalog as saved.
    ``get`` returns None for an unknown catalog. ``list_all`` returns every catalog.
    """

    @abstractmethod
    def get(self, entity_id: EntityId | ModelEntityId) -> Catalog | None:
        """Return the catalog with the given id, or None when there is none."""

    @abstractmethod
    def update(self, catalog: Catalog) -> Catalog:
        """Save the changed catalog and return it as saved.

        Raises ConflictError when the stored catalog is no longer at ``catalog.entity_version``.
        """

    @abstractmethod
    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Delete the catalog; one that still holds namespaces is refused, never emptied."""
