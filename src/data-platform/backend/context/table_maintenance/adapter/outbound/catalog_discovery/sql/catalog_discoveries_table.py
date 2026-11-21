"""Define the catalog_discoveries SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Column, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

catalog_discoveries_table = Table(
    "catalog_discoveries",
    metadata,
    Column("catalog", String, primary_key=True),
    Column("last_discovered_at", UtcDateTime, nullable=True),
    Column("failure_reason", String, nullable=True),
    Column("failure_detail", String, nullable=True),
    Column("failed_at", UtcDateTime, nullable=True),
)
