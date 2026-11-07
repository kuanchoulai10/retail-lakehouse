"""Define the table_maintenance_presets SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import metadata, UtcDateTime

table_maintenance_presets_table = Table(
    "table_maintenance_presets",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("settings_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
