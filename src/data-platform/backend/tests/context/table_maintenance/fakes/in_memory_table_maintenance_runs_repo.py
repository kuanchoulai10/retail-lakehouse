"""Define the InMemoryTableMaintenanceRunsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    TableMaintenanceRunsRepo,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        TableMaintenanceRun,
    )
    from context.table_maintenance.application.domain.model.table import TableId
    from base import EntityId


class InMemoryTableMaintenanceRunsRepo(TableMaintenanceRunsRepo):
    """Keep maintenance runs in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMaintenanceRun] = {}

    def create(self, entity: TableMaintenanceRun) -> TableMaintenanceRun:
        """Insert a run."""
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenanceRun | None:
        """Return the run or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableMaintenanceRun]:
        """Return all runs."""
        return list(self.items.values())

    def update(self, run: TableMaintenanceRun) -> TableMaintenanceRun:
        """Replace a stored run."""
        if run.id.value not in self.items:
            raise LookupError(f"maintenance run {run.id.value} does not exist")
        self.items[run.id.value] = run
        return run

    def list_by_table(
        self, table_uuid: TableId, limit: int = 50
    ) -> list[TableMaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""
        runs = [r for r in self.items.values() if r.table_uuid == table_uuid]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]

    def list_by_table_since(
        self, table_uuid: TableId, since: datetime
    ) -> list[TableMaintenanceRun]:
        """Return the table's runs created at or after since, newest first."""
        runs = [
            r
            for r in self.items.values()
            if r.table_uuid == table_uuid and r.created_at >= since
        ]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs
