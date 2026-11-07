"""Define the tables SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Index, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import metadata, UtcDateTime

tables_table = Table(
    "tables",
    metadata,
    Column("uuid", String, primary_key=True),
    Column("catalog", String, nullable=False),
    Column("namespace", String, nullable=False),
    Column("table_name", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("selection", String, nullable=False),
    Column("settings_json", JSON, nullable=True),
    Column("matched_rule_id", String, nullable=True),
    Column("source_preset_id", String, nullable=True),
    Column("registered_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Column("operation_states_json", JSON, nullable=False),
    Index("ix_tables_name", "catalog", "namespace", "table_name"),
)
