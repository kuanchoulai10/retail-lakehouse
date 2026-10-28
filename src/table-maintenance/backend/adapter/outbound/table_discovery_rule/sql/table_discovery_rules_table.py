"""Define the table_discovery_rules SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String, Table

from adapter.outbound.shared.sql.metadata import metadata
from adapter.outbound.shared.sql.utc_date_time import UtcDateTime

table_discovery_rules_table = Table(
    "table_discovery_rules",
    metadata,
    Column("id", String, primary_key=True),
    Column("priority", Integer, nullable=False),
    Column("effect", String, nullable=False),
    Column("pattern_catalog", String, nullable=False),
    Column("pattern_namespace", String, nullable=False),
    Column("pattern_table", String, nullable=False),
    Column("preset_id", String, nullable=True, index=True),
    Column("enabled", Boolean, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
