"""Define the table_discovery_settings SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, String, Table

from adapter.outbound.sql.metadata import metadata
from adapter.outbound.sql.utc_date_time import UtcDateTime

table_discovery_settings_table = Table(
    "table_discovery_settings",
    metadata,
    Column("id", String, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
