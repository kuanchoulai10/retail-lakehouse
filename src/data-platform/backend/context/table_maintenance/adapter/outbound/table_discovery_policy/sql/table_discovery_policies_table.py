"""Define the table_discovery_policies SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Column, Index, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_discovery_policies_table = Table(
    "table_discovery_policies",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Index("uq_table_discovery_policies_name", "name", unique=True),
)
