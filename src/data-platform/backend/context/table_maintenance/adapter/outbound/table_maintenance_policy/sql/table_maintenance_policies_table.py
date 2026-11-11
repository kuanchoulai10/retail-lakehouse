"""Define the table_maintenance_policies SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_maintenance_policies_table = Table(
    "table_maintenance_policies",
    metadata,
    Column("name", String, primary_key=True),
    Column("version", Integer, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
