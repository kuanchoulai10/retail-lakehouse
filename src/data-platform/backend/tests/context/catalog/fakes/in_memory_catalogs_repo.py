"""Define the InMemoryCatalogsRepo fake."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.outbound.catalog import CatalogsRepo

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.application.port.outbound.catalog import Catalog

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def _copy(catalog: Catalog, **changes: object) -> Catalog:
    return replace(catalog, properties=dict(catalog.properties), **changes)


class InMemoryCatalogsRepo(CatalogsRepo):
    """Keep catalogs by name and guard updates with the entity version, like Polaris.

    Stored catalogs are copies, so a caller changing a loaded catalog changes nothing until it saves.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, Catalog] = {}

    def create(self, entity: Catalog) -> Catalog:
        """Store a new catalog at version 1; a taken name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"Catalog already exists: {entity.id.value}")
        self.items[entity.id.value] = _copy(entity, entity_version=1, created_at=NOW, updated_at=NOW)
        return _copy(self.items[entity.id.value])

    def get(self, entity_id: EntityId) -> Catalog | None:
        """Return a copy of the catalog, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else _copy(stored)

    def list_all(self) -> list[Catalog]:
        """Return every catalog ordered by name."""
        return [_copy(self.items[name]) for name in sorted(self.items)]

    def update(self, catalog: Catalog) -> Catalog:
        """Replace the catalog when its entity version is current, then bump the version."""
        stored = self.items.get(catalog.id.value)
        if stored is None:
            raise NotFoundError(f"Catalog not found: {catalog.id.value}")
        if stored.entity_version != catalog.entity_version:
            raise ConflictError(f"entity version {catalog.entity_version} is not current ({stored.entity_version})")
        self.items[catalog.id.value] = _copy(catalog, entity_version=stored.entity_version + 1, updated_at=NOW)
        return _copy(self.items[catalog.id.value])

    def delete(self, entity_id: EntityId) -> None:
        """Remove the catalog; an unknown one raises NotFoundError."""
        if self.items.pop(entity_id.value, None) is None:
            raise NotFoundError(f"Catalog not found: {entity_id.value}")
