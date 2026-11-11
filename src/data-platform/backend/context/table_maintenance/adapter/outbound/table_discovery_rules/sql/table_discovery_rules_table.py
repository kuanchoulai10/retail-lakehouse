"""Define the table_discovery_rules SQLAlchemy table: one row per rule list, holding its version."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import metadata

table_discovery_rules_table = Table(
    "table_discovery_rules",
    metadata,
    Column("id", String, primary_key=True),
    Column("version", Integer, nullable=False),
)
