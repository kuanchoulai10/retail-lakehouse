"""Define the policy_templates SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, String, Table

from adapter.outbound.sql.metadata import metadata
from adapter.outbound.sql.utc_date_time import UtcDateTime

policy_templates_table = Table(
    "policy_templates",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("settings_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
