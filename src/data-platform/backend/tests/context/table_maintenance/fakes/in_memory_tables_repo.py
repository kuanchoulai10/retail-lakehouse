"""Define the InMemoryTablesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table import TablesRepo

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from base import EntityId
    from context.table_maintenance.application.domain.model.table import (
        Table,
        TableId,
        TableName,
    )


class InMemoryTablesRepo(TablesRepo):
    """Keep tables in a dict keyed by uuid; ``commit_writes`` logs each narrow last-commit write."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, Table] = {}
        self.commit_writes: list[tuple[str, datetime]] = []

    def create(self, entity: Table) -> Table:
        """Insert a table; a duplicate uuid raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"table {entity.id.value} exists")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> Table | None:
        """Return the table or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[Table]:
        """Return tables ordered by name."""
        return sorted(
            self.items.values(),
            key=lambda t: (t.name.catalog, t.name.namespace, t.name.table, t.id.value),
        )

    def update(self, table: Table) -> Table:
        """Replace a stored table."""
        if table.id.value not in self.items:
            raise LookupError(f"table {table.id.value} does not exist")
        self.items[table.id.value] = table
        return table

    def record_last_commit(self, table_id: TableId, at: datetime) -> bool:
        """Move the stored table's last commit by the aggregate's own rule."""
        self.commit_writes.append((table_id.value, at))
        stored = self.items.get(table_id.value)
        return stored is not None and stored.record_last_commit(at)

    def find_by_name(self, name: TableName) -> Table | None:
        """Return the latest-updated non-dropped table with this name."""
        matches = [t for t in self.items.values() if t.name == name and t.status != TableStatus.DROPPED]
        return max(matches, key=lambda t: t.updated_at, default=None)

    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[Table]:
        """Return tables whose status is in ``statuses``."""
        return [t for t in self.list_all() if t.status in statuses]
