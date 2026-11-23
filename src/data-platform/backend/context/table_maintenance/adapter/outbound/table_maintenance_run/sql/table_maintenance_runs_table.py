"""Define the table_maintenance_runs SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Index, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_maintenance_runs_table = Table(
    "table_maintenance_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("table_uuid", String, nullable=False),
    Column("execution_ref", String, nullable=False),
    Column("trigger", String, nullable=False),
    Column("operation", String, nullable=False),
    Column("priority", String, nullable=False),
    Column("status", String, nullable=False),
    Column("error", String, nullable=True),
    Column("skip_reason", String, nullable=True),
    Column("filters_json", JSON, nullable=False),
    Column("procedure_args_json", JSON, nullable=False),
    Column("metrics_json", JSON, nullable=False),
    Column("attempts_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("finished_at", UtcDateTime, nullable=True),
    Index("ix_table_maintenance_runs_table_created", "table_uuid", "created_at"),
)
