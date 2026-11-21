"""Define the TablesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table import Table

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import OverTargetPartition
    from context.table_maintenance.application.domain.model.table import (
        TableId,
        TableName,
        TableStatus,
    )


class TablesRepo(Repository[Table]):
    """Persist and query Table aggregates."""

    @abstractmethod
    def update(self, table: Table) -> Table:
        """Persist the changed table and return it.

        The stored last commit never moves back: an older one, or none, leaves it as stored.
        The stored over-target partitions are never written: only ``record_over_target_partitions`` does.
        """

    @abstractmethod
    def record_last_commit(self, table_id: TableId, at: datetime) -> bool:
        """Move the stored table's last commit to ``at``; return whether it moved.

        It moves under the rule of ``Table.record_last_commit``: only forward, and never
        once the table is dropped. Nothing else of the table is written, so a caller
        holding an older copy of it cannot put back what another writer stored since.
        """

    @abstractmethod
    def record_over_target_partitions(self, table_id: TableId, partitions: Sequence[OverTargetPartition]) -> bool:
        """Replace the stored table's over-target partitions; return whether a row matched.

        A row matches when the table exists and is not dropped. It does not say whether the
        value changed, which a SQL write cannot tell: ``Table.record_over_target_partitions``
        holds that rule and the caller gates on it. Nothing else of the table is written, so a
        caller holding an older copy of it cannot put back what another writer stored since.
        """

    @abstractmethod
    def find_by_name(self, name: TableName) -> Table | None:
        """Return the non-dropped table with this name (latest updated), or None."""

    @abstractmethod
    def list_by_statuses(self, statuses: Sequence[TableStatus]) -> list[Table]:
        """Return the tables whose status is one of ``statuses``."""
