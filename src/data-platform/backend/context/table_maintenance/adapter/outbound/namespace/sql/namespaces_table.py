"""Define the namespaces SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

namespaces_table = Table(
    "namespaces",
    metadata,
    Column("id", String, primary_key=True),
    Column("catalog", String, nullable=False),
    Column("path_json", JSON, nullable=False),
    Column("discovery_policy_id", String, ForeignKey("table_discovery_policies.id"), nullable=True),
    Column("maintenance_policy_id", String, ForeignKey("table_maintenance_policies.id"), nullable=True),
    Column("version", Integer, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Index("ix_namespaces_catalog", "catalog"),
    Index("ix_namespaces_discovery_policy_id", "discovery_policy_id"),
    Index("ix_namespaces_maintenance_policy_id", "maintenance_policy_id"),
)
