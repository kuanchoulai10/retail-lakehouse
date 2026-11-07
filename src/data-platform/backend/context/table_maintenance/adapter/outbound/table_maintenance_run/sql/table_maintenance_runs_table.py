"""Define the table_maintenance_runs SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Index, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import metadata, UtcDateTime

table_maintenance_runs_table = Table(
    "table_maintenance_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("table_uuid", String, nullable=False),
    Column("execution_ref", String, nullable=False),
    Column("trigger", String, nullable=False),
    Column("operations_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("finished_at", UtcDateTime, nullable=True),
    Index("ix_table_maintenance_runs_table_created", "table_uuid", "created_at"),
)
