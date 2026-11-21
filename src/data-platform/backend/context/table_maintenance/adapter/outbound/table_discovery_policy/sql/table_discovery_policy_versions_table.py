"""Define the table_discovery_policy_versions SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_discovery_policy_versions_table = Table(
    "table_discovery_policy_versions",
    metadata,
    Column("policy_id", String, ForeignKey("table_discovery_policies.id"), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("content_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
)
