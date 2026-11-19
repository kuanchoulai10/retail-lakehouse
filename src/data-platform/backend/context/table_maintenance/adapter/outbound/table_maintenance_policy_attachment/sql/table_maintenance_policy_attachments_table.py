"""Define the table_maintenance_policy_attachments SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, Index, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_maintenance_policy_attachments_table = Table(
    "table_maintenance_policy_attachments",
    metadata,
    Column("id", String, primary_key=True),
    Column("target_key", String, nullable=False),
    Column("target_type", String, nullable=False),
    Column("path_json", JSON, nullable=False),
    Column("table_uuid", String, nullable=True),
    Column("policy_name", String, ForeignKey("table_maintenance_policies.name"), nullable=False),
    Column("attached_at", UtcDateTime, nullable=False),
    Index("ix_table_maintenance_policy_attachments_policy_name", "policy_name"),
    Index("uq_table_maintenance_policy_attachments_target_key", "target_key", unique=True),
)
