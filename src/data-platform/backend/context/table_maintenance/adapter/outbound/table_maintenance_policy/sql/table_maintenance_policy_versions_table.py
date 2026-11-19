"""Define the table_maintenance_policy_versions SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_maintenance_policy_versions_table = Table(
    "table_maintenance_policy_versions",
    metadata,
    Column("policy_id", String, ForeignKey("table_maintenance_policies.id"), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("content_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
)
