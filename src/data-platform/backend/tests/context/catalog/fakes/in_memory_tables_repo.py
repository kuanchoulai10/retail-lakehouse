"""Define the InMemoryTablesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from base import validated_copy
from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.outbound.table import Table, TableId, TablesRepo

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.application.port.outbound.table import NamespaceId

LAST_UPDATED_MS = 1762516800000


def _copy(table: Table, **changes: object) -> Table:
    """Return a validated copy; it shares no mutable state with table and holds no pending events."""
    return validated_copy(table, **changes)


class InMemoryTablesRepo(TablesRepo):
    """Keep tables by id and behave like the catalog: it assigns the uuid and guards commits with it.

    Each created table gets the next uuid, ``uuid-1``, ``uuid-2`` and so on, so a table dropped
    and created again under the same name is a different table.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, Table] = {}
        self._uuids_issued = 0

    def create(self, entity: Table) -> Table:
        """Store a new table with a fresh uuid; a taken name raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"Table already exists: {entity.id.name}")
        self._uuids_issued += 1
        location = entity.location or f"s3://warehouse/{'/'.join(entity.id.namespace)}/{entity.id.name}"
        self.items[entity.id.value] = _copy(
            entity,
            uuid=f"uuid-{self._uuids_issued}",
            format_version=2,
            location=location,
            last_updated_ms=LAST_UPDATED_MS,
        )
        return _copy(self.items[entity.id.value])

    def get(self, entity_id: EntityId) -> Table | None:
        """Return a copy of the table, or None."""
        stored = self.items.get(entity_id.value)
        return None if stored is None else _copy(stored)

    def list_all(self) -> list[Table]:
        """Return every table ordered by id."""
        return [_copy(self.items[key]) for key in sorted(self.items)]

    def list_in(self, namespace: NamespaceId) -> list[TableId]:
        """Return the ids of the tables directly in ``namespace``."""
        found = []
        for key in sorted(self.items):
            table_id = TableId(key)
            if table_id.catalog == namespace.catalog and table_id.namespace == namespace.parts:
                found.append(table_id)
        return found

    def rename(self, source: TableId, target: TableId) -> None:
        """Move the table; an unknown source raises NotFoundError, a taken target ConflictError."""
        stored = self.items.get(source.value)
        if stored is None:
            raise NotFoundError(f"Table does not exist: {source.name}")
        if target.value in self.items:
            raise ConflictError(f"Table already exists: {target.name}")
        del self.items[source.value]
        self.items[target.value] = _copy(stored, id=target)

    def update_properties(
        self, entity_id: TableId, expected_uuid: str, updates: dict[str, str], removals: list[str]
    ) -> Table:
        """Apply removals then updates when the uuid matches; otherwise ConflictError, like a failed requirement."""
        stored = self.items.get(entity_id.value)
        if stored is None:
            raise NotFoundError(f"Table does not exist: {entity_id.name}")
        if stored.uuid != expected_uuid:
            raise ConflictError(f"Requirement failed: UUID does not match: expected {expected_uuid} != {stored.uuid}")
        properties = {key: value for key, value in stored.properties.items() if key not in removals}
        properties.update(updates)
        self.items[entity_id.value] = _copy(stored, properties=properties)
        return _copy(self.items[entity_id.value])

    def delete(self, entity_id: EntityId) -> None:
        """Remove the table without purging its files; an unknown one raises NotFoundError."""
        if self.items.pop(entity_id.value, None) is None:
            raise NotFoundError(f"Table does not exist: {entity_id.value}")
