"""Define the compaction_rounds SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Float, Index, Integer, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

compaction_rounds_table = Table(
    "compaction_rounds",
    metadata,
    Column("id", String, primary_key=True),
    Column("started_at", UtcDateTime, nullable=False),
    Column("budget_gb_hours", Float, nullable=False),
    Column("used_gb_hours", Float, nullable=False),
    Column("picks_json", JSON, nullable=False),
    Column("skips_json", JSON, nullable=False),
    Column("skipped_total", Integer, nullable=False),
    Index("ix_compaction_rounds_started_at", "started_at"),
)
