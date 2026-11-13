"""Define the compaction_candidates SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, Float, Index, Integer, String, Table, UniqueConstraint

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata

compaction_candidates_table = Table(
    "compaction_candidates",
    metadata,
    Column("id", String, primary_key=True),
    Column("table_uuid", String, nullable=False),
    Column("partition_key", String, nullable=False),
    Column("spec_id", Integer, nullable=False),
    Column("label", String, nullable=False),
    Column("state", String, nullable=False),
    Column("hold_reason", String, nullable=True),
    Column("reducible_files", BigInteger, nullable=False),
    Column("data_bytes", BigInteger, nullable=False),
    Column("estimated_gb_hours", Float, nullable=False),
    Column("score", Float, nullable=False),
    Column("last_written_at", UtcDateTime, nullable=True),
    Column("waiting_since", UtcDateTime, nullable=True),
    Column("observed_at", UtcDateTime, nullable=False),
    Column("claimed_by_run_id", String, nullable=True),
    Column("lease_expires_at", UtcDateTime, nullable=True),
    Column("updated_at", UtcDateTime, nullable=False),
    UniqueConstraint("table_uuid", "partition_key", name="uq_compaction_candidates_table_partition"),
    Index("ix_compaction_candidates_table_state", "table_uuid", "state"),
    Index("ix_compaction_candidates_claimed_by_run", "claimed_by_run_id"),
)
