"""Define the table_reconciliations SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, Index, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_reconciliations_table = Table(
    "table_reconciliations",
    metadata,
    Column("id", String, primary_key=True),
    Column("table_uuid", String, nullable=False),
    Column("reconciled_at", UtcDateTime, nullable=False),
    Column("wake_reasons_json", JSON, nullable=False),
    Column("dry_run", Boolean, nullable=False),
    Column("outcome", String, nullable=False),
    Column("skip_reason", String, nullable=True),
    Column("operations_json", JSON, nullable=False),
    Column("run_id", String, nullable=True),
    Index("ix_table_reconciliations_table_reconciled", "table_uuid", "reconciled_at"),
)
