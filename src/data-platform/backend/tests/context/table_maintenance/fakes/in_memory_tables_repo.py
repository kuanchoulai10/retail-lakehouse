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
    from context.table_maintenance.application.domain.model.shared import OverTargetPartition, TableId
    from context.table_maintenance.application.domain.model.table import Table, TableName


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
        """Replace a stored table, keeping the stored over-target partitions as the SQL adapter does."""
        stored = self.items.get(table.id.value)
        if stored is None:
            raise LookupError(f"table {table.id.value} does not exist")
        table.over_target_partitions = stored.over_target_partitions
        self.items[table.id.value] = table
        return table

    def record_last_commit(self, table_id: TableId, at: datetime) -> bool:
        """Move the stored table's last commit by the aggregate's own rule."""
        self.commit_writes.append((table_id.value, at))
        stored = self.items.get(table_id.value)
        return stored is not None and stored.record_last_commit(at)

    def record_over_target_partitions(self, table_id: TableId, partitions: Sequence[OverTargetPartition]) -> bool:
        """Replace the stored table's over-target partitions; return whether a live row matched."""
        stored = self.items.get(table_id.value)
        if stored is None or stored.status == TableStatus.DROPPED:
            return False
        stored.record_over_target_partitions(partitions)
        return True

    def find_by_name(self, name: TableName) -> Table | None:
        """Return the latest-updated non-dropped table with this name."""
        matches = [t for t in self.items.values() if t.name == name and t.status != TableStatus.DROPPED]
        return max(matches, key=lambda t: t.updated_at, default=None)

    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[Table]:
        """Return tables whose status is in ``statuses``."""
        return [t for t in self.list_all() if t.status in statuses]

    def list_catalogs_with_managed_tables(self) -> list[str]:
        """Return each catalog that holds a managed table, once and sorted."""
        return sorted({t.name.catalog for t in self.list_all() if t.status == TableStatus.MANAGED})
