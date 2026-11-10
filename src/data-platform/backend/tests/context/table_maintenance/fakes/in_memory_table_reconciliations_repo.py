"""Define the InMemoryTableReconciliationsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_reconciliation import (
    TableReconciliationsRepo,
)

if TYPE_CHECKING:
    from datetime import datetime

    from base import EntityId
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_reconciliation import (
        TableReconciliation,
    )


class InMemoryTableReconciliationsRepo(TableReconciliationsRepo):
    """Keep reconciliations in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableReconciliation] = {}

    def create(self, entity: TableReconciliation) -> TableReconciliation:
        """Insert a reconciliation."""
        if entity.id.value in self.items:
            raise ConflictError(f"reconciliation {entity.id.value} already exists")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> TableReconciliation | None:
        """Return the reconciliation or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableReconciliation]:
        """Return all reconciliations."""
        return list(self.items.values())

    def list_by_table(
        self,
        table_uuid: TableId,
        *,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[TableReconciliation]:
        """Return up to ``limit`` reconciliations of the table, newest first, strictly before ``before``."""
        found = [
            r
            for r in self.items.values()
            if r.table_uuid == table_uuid and (before is None or r.reconciled_at < before)
        ]
        found.sort(key=lambda r: r.reconciled_at, reverse=True)
        return found[:limit]

    def delete_older_than(self, table_uuid: TableId, cutoff: datetime) -> int:
        """Delete the table's reconciliations before ``cutoff`` and return how many went."""
        doomed = [k for k, r in self.items.items() if r.table_uuid == table_uuid and r.reconciled_at < cutoff]
        for key in doomed:
            del self.items[key]
        return len(doomed)
