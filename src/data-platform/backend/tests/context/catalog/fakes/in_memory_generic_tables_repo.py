"""Define the InMemoryGenericTablesRepo fake."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.outbound.generic_table import (
    GenericTable,
    GenericTableId,
    GenericTablesRepo,
)

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.application.port.outbound.generic_table import NamespaceId


class InMemoryGenericTablesRepo(GenericTablesRepo):
    """Keep generic tables by id and behave like the catalog: a taken name conflicts, an unknown one is absent."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, GenericTable] = {}

    def create(self, entity: GenericTable) -> GenericTable:
        """Store a new generic table; a taken name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"Generic table already exists: {entity.id.name}")
        self.items[entity.id.value] = replace(entity, properties=dict(entity.properties))
        return replace(entity, properties=dict(entity.properties))

    def get(self, entity_id: EntityId) -> GenericTable | None:
        """Return a copy of the generic table, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else replace(stored, properties=dict(stored.properties))

    def list_all(self) -> list[GenericTable]:
        """Return every generic table ordered by id."""
        return [replace(self.items[key]) for key in sorted(self.items)]

    def list_in(self, namespace: NamespaceId) -> list[GenericTableId]:
        """Return the ids of the generic tables directly in ``namespace``."""
        found = []
        for key in sorted(self.items):
            table_id = GenericTableId(key)
            if table_id.catalog == namespace.catalog and table_id.namespace == namespace.parts:
                found.append(table_id)
        return found

    def delete(self, entity_id: EntityId) -> None:
        """Remove the generic table; an unknown one raises NotFoundError."""
        if self.items.pop(entity_id.value, None) is None:
            raise NotFoundError(f"Generic table does not exist: {entity_id.value}")
