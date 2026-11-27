"""Define the catalogs SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

catalogs_table = Table(
    "catalogs",
    metadata,
    Column("name", String, primary_key=True),
    Column("discovery_policy_id", String, ForeignKey("table_discovery_policies.id"), nullable=True),
    Column("maintenance_policy_id", String, ForeignKey("table_maintenance_policies.id"), nullable=True),
    Column("version", Integer, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    Index("ix_catalogs_discovery_policy_id", "discovery_policy_id"),
    Index("ix_catalogs_maintenance_policy_id", "maintenance_policy_id"),
)
