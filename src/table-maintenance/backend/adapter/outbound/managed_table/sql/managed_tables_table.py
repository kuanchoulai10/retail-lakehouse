"""Define the managed_tables SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Index, String, Table

from adapter.outbound.sql.metadata import metadata
from adapter.outbound.sql.utc_date_time import UtcDateTime

managed_tables_table = Table(
    "managed_tables",
    metadata,
    Column("uuid", String, primary_key=True),
    Column("catalog", String, nullable=False),
    Column("namespace", String, nullable=False),
    Column("table_name", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("selection", String, nullable=False),
    Column("settings_json", JSON, nullable=True),
    Column("matched_rule_id", String, nullable=True),
    Column("source_template_id", String, nullable=True),
    Column("registered_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Column("operation_states_json", JSON, nullable=False),
    Index("ix_managed_tables_name", "catalog", "namespace", "table_name"),
)
