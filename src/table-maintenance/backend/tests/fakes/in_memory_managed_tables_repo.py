"""Define the InMemoryManagedTablesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.managed_table.table_status import TableStatus
from application.exceptions import ConflictError
from application.port.outbound.managed_table.managed_tables_repo import (
    ManagedTablesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from application.domain.model.managed_table.managed_table import ManagedTable
    from application.domain.model.managed_table.table_name import TableName
    from base.entity_id import EntityId


class InMemoryManagedTablesRepo(ManagedTablesRepo):
    """Keep managed tables in a dict keyed by uuid."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, ManagedTable] = {}

    def create(self, entity: ManagedTable) -> ManagedTable:
        """Insert a table; a duplicate uuid raises ConflictError."""
        if entity.id.value in self.items:
            raise ConflictError(f"table {entity.id.value} exists")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> ManagedTable | None:
        """Return the table or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[ManagedTable]:
        """Return tables ordered by name."""
        return sorted(
            self.items.values(),
            key=lambda t: (t.name.catalog, t.name.namespace, t.name.table, t.id.value),
        )

    def update(self, table: ManagedTable) -> ManagedTable:
        """Replace a stored table."""
        if table.id.value not in self.items:
            raise LookupError(f"managed table {table.id.value} does not exist")
        self.items[table.id.value] = table
        return table

    def find_by_name(self, name: TableName) -> ManagedTable | None:
        """Return the latest-updated non-dropped table with this name."""
        matches = [
            t
            for t in self.items.values()
            if t.name == name and t.status != TableStatus.DROPPED
        ]
        return max(matches, key=lambda t: t.updated_at, default=None)

    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[ManagedTable]:
        """Return tables whose status is in ``statuses``."""
        return [t for t in self.list_all() if t.status in statuses]
