"""Define the table_maintenance_presets SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, String, Table

from adapter.outbound.shared.sql.metadata import metadata
from adapter.outbound.shared.sql.utc_date_time import UtcDateTime

table_maintenance_presets_table = Table(
    "table_maintenance_presets",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("settings_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
