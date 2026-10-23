"""Define the InMemoryMaintenanceRunsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.maintenance_run.maintenance_runs_repo import (
    MaintenanceRunsRepo,
)

if TYPE_CHECKING:
    from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
    from application.domain.model.managed_table.table_uuid import TableUuid
    from base.entity_id import EntityId


class InMemoryMaintenanceRunsRepo(MaintenanceRunsRepo):
    """Keep maintenance runs in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, MaintenanceRun] = {}

    def create(self, entity: MaintenanceRun) -> MaintenanceRun:
        """Insert a run."""
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> MaintenanceRun | None:
        """Return the run or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[MaintenanceRun]:
        """Return all runs."""
        return list(self.items.values())

    def update(self, run: MaintenanceRun) -> MaintenanceRun:
        """Replace a stored run."""
        if run.id.value not in self.items:
            raise LookupError(f"maintenance run {run.id.value} does not exist")
        self.items[run.id.value] = run
        return run

    def list_by_table(
        self, table_uuid: TableUuid, limit: int = 50
    ) -> list[MaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""
        runs = [r for r in self.items.values() if r.table_uuid == table_uuid]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]
