"""Define the TableMaintenanceRunsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from application.domain.model.table_maintenance_run import TableMaintenanceRun
from base import Repository

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.table import TableId


class TableMaintenanceRunsRepo(Repository[TableMaintenanceRun]):
    """Persist and query TableMaintenanceRun aggregates."""

    @abstractmethod
    def update(self, run: TableMaintenanceRun) -> TableMaintenanceRun:
        """Persist the changed run and return it."""

    @abstractmethod
    def list_by_table(
        self, table_uuid: TableId, limit: int = 50
    ) -> list[TableMaintenanceRun]:
        """Return up to ``limit`` runs of the table, newest first."""

    @abstractmethod
    def list_by_table_since(
        self, table_uuid: TableId, since: datetime
    ) -> list[TableMaintenanceRun]:
        """Return the table's runs created at or after since, newest first."""
