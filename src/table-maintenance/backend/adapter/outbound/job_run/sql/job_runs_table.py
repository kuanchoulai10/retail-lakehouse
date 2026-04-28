"""Define the job_runs SQLAlchemy table schema."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.types import JSON

from adapter.outbound.sql.metadata import metadata

job_runs_table = Table(
    "job_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("job_id", String, ForeignKey("jobs.id"), nullable=False),
    Column("status", String, nullable=False),
    Column("trigger_type", String, nullable=False, default="manual"),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("error", String, nullable=True),
    Column("result_duration_ms", Integer, nullable=True),
    Column("result_metadata", JSON, nullable=True),
)
