"""Define the TableReconciliationsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_reconciliation import (
    TableReconciliation,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import TableId


class TableReconciliationsRepo(Repository[TableReconciliation]):
    """Persist and query TableReconciliation aggregates."""

    @abstractmethod
    def list_by_table(
        self,
        table_uuid: TableId,
        *,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[TableReconciliation]:
        """Return up to ``limit`` reconciliations of the table, newest first, strictly before ``before``."""

    @abstractmethod
    def delete_older_than(self, table_uuid: TableId, cutoff: datetime) -> int:
        """Delete the table's reconciliations before ``cutoff`` and return how many went."""
