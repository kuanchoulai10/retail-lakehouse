"""Define the TablesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from application.domain.model.table import Table
from base import Repository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from application.domain.model.table import TableName, TableStatus


class TablesRepo(Repository[Table]):
    """Persist and query Table aggregates."""

    @abstractmethod
    def update(self, table: Table) -> Table:
        """Persist the changed table and return it."""

    @abstractmethod
    def find_by_name(self, name: TableName) -> Table | None:
        """Return the non-dropped table with this name (latest updated), or None."""

    @abstractmethod
    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[Table]:
        """Return the tables whose status is one of ``statuses``."""
