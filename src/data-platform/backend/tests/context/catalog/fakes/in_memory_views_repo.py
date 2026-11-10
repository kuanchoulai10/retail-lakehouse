"""Define the InMemoryViewsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from base.model import validated_copy
from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.outbound.view import View, ViewId, ViewsRepo

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.application.port.outbound.view import NamespaceId


def _copy(view: View, **changes: object) -> View:
    """Return a validated copy; it shares no mutable state with view and holds no pending events."""
    return validated_copy(view, **changes)


class InMemoryViewsRepo(ViewsRepo):
    """Keep views by id and behave like the catalog: it assigns the uuid and the location."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, View] = {}
        self._uuids_issued = 0

    def create(self, entity: View) -> View:
        """Store a new view with a fresh uuid; a taken name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"View already exists: {entity.id.name}")
        self._uuids_issued += 1
        location = entity.location or f"s3://warehouse/{'/'.join(entity.id.namespace)}/{entity.id.name}"
        self.items[entity.id.value] = _copy(entity, uuid=f"view-uuid-{self._uuids_issued}", location=location)
        return _copy(self.items[entity.id.value])

    def get(self, entity_id: EntityId | ModelEntityId) -> View | None:
        """Return a copy of the view, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else _copy(stored)

    def list_all(self) -> list[View]:
        """Return every view ordered by id."""
        return [_copy(self.items[key]) for key in sorted(self.items)]

    def list_in(self, namespace: NamespaceId) -> list[ViewId]:
        """Return the ids of the views directly in ``namespace``."""
        found = []
        for key in sorted(self.items):
            view_id = ViewId(key)
            if view_id.catalog == namespace.catalog and view_id.namespace == namespace.parts:
                found.append(view_id)
        return found

    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """Remove the view; an unknown one raises NotFoundError."""
        if self.items.pop(entity_id.value, None) is None:
            raise NotFoundError(f"View does not exist: {entity_id.value}")
