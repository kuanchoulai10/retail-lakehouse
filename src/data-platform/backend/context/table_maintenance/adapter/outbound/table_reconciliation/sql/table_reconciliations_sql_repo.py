"""Define the TableReconciliationsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_reconciliation.sql.table_reconciliation_row_mapper import (
    TableReconciliationRowMapper,
)
from context.table_maintenance.adapter.outbound.table_reconciliation.sql.table_reconciliations_table import (
    table_reconciliations_table as t,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_reconciliation import (
    TableReconciliationsRepo,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableId,
        TableReconciliation,
    )


class TableReconciliationsSqlRepo(TableReconciliationsRepo):
    """Store TableReconciliation aggregates in a SQL database.

    The wake reasons and operations of a reconciliation are stored as JSON on its row.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableReconciliation) -> TableReconciliation:
        """Insert a new reconciliation."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**TableReconciliationRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableReconciliation | None:
        """Return the reconciliation with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else TableReconciliationRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[TableReconciliation]:
        """Return all reconciliations, newest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.reconciled_at.desc(), t.c.id.desc())).all()
        return [TableReconciliationRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_by_table(
        self,
        table_uuid: TableId,
        *,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[TableReconciliation]:
        """Return up to ``limit`` reconciliations of the table, newest first, strictly before ``before``."""
        stmt = select(t).where(t.c.table_uuid == table_uuid.value)
        if before is not None:
            stmt = stmt.where(t.c.reconciled_at < before)
        stmt = stmt.order_by(t.c.reconciled_at.desc(), t.c.id.desc()).limit(limit)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [TableReconciliationRowMapper.to_aggregate(r._mapping) for r in rows]

    def delete_older_than(self, table_uuid: TableId, cutoff: datetime) -> int:
        """Delete the table's reconciliations before ``cutoff`` and return how many went."""
        with self._engine.begin() as conn:
            result = conn.execute(delete(t).where(t.c.table_uuid == table_uuid.value, t.c.reconciled_at < cutoff))
        return result.rowcount
