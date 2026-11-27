"""Define the InMemoryCatalogsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.port.outbound.catalog import Catalog


class InMemoryCatalogsRepo(CatalogsRepo):
    """Keep catalogs in a dict keyed by name, saving each under compare-and-set as the SQL adapter does."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, Catalog] = {}

    def create(self, entity: Catalog) -> Catalog:
        """Insert a catalog; a stored name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"catalog {entity.id.value} exists")
        self.items[entity.id.value] = entity.model_copy(deep=True)
        return entity

    def get(self, entity_id: EntityId) -> Catalog | None:
        """Return a copy of the stored catalog, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else stored.model_copy(deep=True)

    def get_many(self, ids: Sequence[EntityId]) -> list[Catalog]:
        """Return copies of the stored catalogs among the ids, by name."""
        wanted = {i.value for i in ids}
        return [c for c in self.list_all() if c.id.value in wanted]

    def list_all(self) -> list[Catalog]:
        """Return copies of every catalog, by name."""
        return [self.items[name].model_copy(deep=True) for name in sorted(self.items)]

    def update(self, catalog: Catalog) -> Catalog:
        """Store a copy at the next version when the stored one is at the catalog's version; return it."""
        stored = self.items.get(catalog.id.value)
        if stored is None:
            raise LookupError(f"catalog {catalog.id.value} does not exist")
        if stored.version != catalog.version:
            raise ConcurrentUpdateError(f"catalog {catalog.id.value} was changed by someone else")
        saved = catalog.model_copy(deep=True, update={"version": catalog.version + 1})
        self.items[catalog.id.value] = saved
        return saved.model_copy(deep=True)
