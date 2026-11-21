"""Define the InMemoryTableMaintenanceRunsRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    MaintenanceOperation,
    TableMaintenanceRunsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from base import EntityId
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        TableMaintenanceRun,
    )


class InMemoryTableMaintenanceRunsRepo(TableMaintenanceRunsRepo):
    """Keep maintenance runs in a dict."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, TableMaintenanceRun] = {}

    def create(self, entity: TableMaintenanceRun) -> TableMaintenanceRun:
        """Insert a run."""
        self.items[entity.id.value] = entity
        return entity

    def create_all(self, runs: Sequence[TableMaintenanceRun]) -> list[TableMaintenanceRun]:
        """Insert runs together, all or none: a run whose id is already used stores none."""
        ids = [run.id.value for run in runs]
        if len(set(ids)) != len(ids) or any(i in self.items for i in ids):
            raise ConflictError(f"maintenance runs {ids} are not all new")
        for run in runs:
            self.items[run.id.value] = run
        return list(runs)

    def get(self, entity_id: EntityId) -> TableMaintenanceRun | None:
        """Return the run or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[TableMaintenanceRun]:
        """Return all runs, newest first, in the SQL repo's order."""
        return sorted(self.items.values(), key=_listing_key, reverse=True)

    def update(self, run: TableMaintenanceRun) -> TableMaintenanceRun:
        """Replace a stored run."""
        if run.id.value not in self.items:
            raise LookupError(f"maintenance run {run.id.value} does not exist")
        self.items[run.id.value] = run
        return run

    def list_by_table(self, table_uuid: TableId, limit: int = 50) -> list[TableMaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first, in the SQL repo's order.

        Among runs of one creation time the plan's last operation lists first, then the larger id.
        """
        runs = [r for r in self.items.values() if r.table_uuid == table_uuid]
        runs.sort(key=_listing_key, reverse=True)
        return runs[:limit]


def _listing_key(run: TableMaintenanceRun) -> tuple[datetime, int, str]:
    return run.created_at, MaintenanceOperation.ordered().index(run.operation), run.id.value
