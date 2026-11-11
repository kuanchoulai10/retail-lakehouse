"""Define the table_discovery_rule_items SQLAlchemy table: one row per rule of a list."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

table_discovery_rule_items_table = Table(
    "table_discovery_rule_items",
    metadata,
    Column("rules_id", String, ForeignKey("table_discovery_rules.id"), primary_key=True),
    Column("id", String, primary_key=True),
    Column("priority", Integer, nullable=False),
    Column("action", String, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("catalogs_json", JSON, nullable=False),
    Column("namespaces_json", JSON, nullable=False),
    Column("tables_json", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
    UniqueConstraint("rules_id", "priority"),
)
