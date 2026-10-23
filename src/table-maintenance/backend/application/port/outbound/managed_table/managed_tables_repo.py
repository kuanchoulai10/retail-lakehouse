"""Define the ManagedTablesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from application.domain.model.managed_table.managed_table import ManagedTable
from base.repository import Repository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from application.domain.model.managed_table.table_name import TableName
    from application.domain.model.managed_table.table_status import TableStatus


class ManagedTablesRepo(Repository[ManagedTable]):
    """Persist and query ManagedTable aggregates."""

    @abstractmethod
    def update(self, table: ManagedTable) -> ManagedTable:
        """Persist the changed table and return it."""

    @abstractmethod
    def find_by_name(self, name: TableName) -> ManagedTable | None:
        """Return the non-dropped table with this name (latest updated), or None."""

    @abstractmethod
    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[ManagedTable]:
        """Return the tables whose status is one of ``statuses``."""
