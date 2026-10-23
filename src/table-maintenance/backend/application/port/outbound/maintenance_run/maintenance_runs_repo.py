"""Define the MaintenanceRunsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from application.domain.model.maintenance_run.maintenance_run import MaintenanceRun
from base.repository import Repository

if TYPE_CHECKING:
    from application.domain.model.managed_table.table_uuid import TableUuid


class MaintenanceRunsRepo(Repository[MaintenanceRun]):
    """Persist and query MaintenanceRun aggregates."""

    @abstractmethod
    def update(self, run: MaintenanceRun) -> MaintenanceRun:
        """Persist the changed run and return it."""

    @abstractmethod
    def list_by_table(
        self, table_uuid: TableUuid, limit: int = 50
    ) -> list[MaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""
