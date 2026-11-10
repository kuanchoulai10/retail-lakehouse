"""Define the InMemoryNamespacesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.outbound.namespace import Namespace, NamespaceId, NamespacesRepo

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.application.port.outbound.namespace import CatalogId


class InMemoryNamespacesRepo(NamespacesRepo):
    """Keep namespaces by id and behave like Polaris: parents must exist, only empty ones are dropped."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, dict[str, str]] = {}

    def create(self, entity: Namespace) -> Namespace:
        """Store a new namespace; a taken id raises ConflictError, a missing parent NotFoundError."""
        key = entity.id.value
        if key in self.items:
            raise ConflictError(f"Namespace already exists: {entity.id.parts}")
        parent = entity.id.parts[:-1]
        if parent and NamespaceId.of(entity.id.catalog, parent).value not in self.items:
            raise NotFoundError(f"Namespace does not exist: {parent}")
        self.items[key] = dict(entity.properties)
        return self._load(entity.id)

    def get(self, entity_id: EntityId | ModelEntityId) -> Namespace | None:
        """Return the namespace, or None."""
        if entity_id.value not in self.items:
            return None
        return self._load(entity_id)

    def list_all(self) -> list[Namespace]:
        """Return every namespace ordered by id."""
        return [self._load(NamespaceId(key)) for key in sorted(self.items)]

    def list_in(self, catalog: CatalogId, parent: tuple[str, ...]) -> list[Namespace]:
        """Return the direct children of ``parent``, without their properties."""
        found = []
        for key in sorted(self.items):
            child = NamespaceId(key)
            if child.catalog == catalog.name and len(child.parts) == len(parent) + 1 and child.parts[:-1] == parent:
                found.append(Namespace(id=child, properties={}))
        return found

    def update_properties(self, entity_id: NamespaceId, updates: dict[str, str], removals: list[str]) -> Namespace:
        """Apply removals then updates; an unknown namespace raises NotFoundError."""
        stored = self.items.get(entity_id.value)
        if stored is None:
            raise NotFoundError(f"Namespace does not exist: {entity_id.value}")
        for key in removals:
            stored.pop(key, None)
        stored.update(updates)
        return self._load(entity_id)

    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Remove the namespace; unknown raises NotFoundError, one with children ConflictError."""
        if entity_id.value not in self.items:
            raise NotFoundError(f"Namespace does not exist: {entity_id.value}")
        prefix = entity_id.value + "\x1f"
        if any(key.startswith(prefix) for key in self.items):
            raise ConflictError(f"Namespace {entity_id.value!r} is not empty")
        del self.items[entity_id.value]

    def _load(self, entity_id: EntityId | ModelEntityId) -> Namespace:
        return Namespace(id=NamespaceId(entity_id.value), properties=dict(self.items[entity_id.value]))
