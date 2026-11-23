"""Define the tables SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Index, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

tables_table = Table(
    "tables",
    metadata,
    Column("uuid", String, primary_key=True),
    Column("catalog", String, nullable=False),
    Column("namespace", String, nullable=False),
    Column("table_name", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("matched_rule_id", String, nullable=True),
    Column("matched_policy_id", String, nullable=False),
    Column("matched_policy_version", Integer, nullable=False),
    Column("registered_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Column("operation_states_json", JSON, nullable=False),
    Column("last_committed_at", UtcDateTime, nullable=True),
    Column("last_discovered_at", UtcDateTime, nullable=True),
    Column("priority", String, nullable=False),
    Column("over_target_partitions_json", JSON, nullable=False),
    Index("ix_tables_name", "catalog", "namespace", "table_name"),
)
