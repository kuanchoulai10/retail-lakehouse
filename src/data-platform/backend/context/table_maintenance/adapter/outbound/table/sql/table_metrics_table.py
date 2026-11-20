"""Define the table_metrics SQLAlchemy table."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, String, Table

from context.table_maintenance.adapter.outbound.shared.sql import UtcDateTime, metadata
from context.table_maintenance.application.port.outbound.table import TABLE_METRIC_COUNT_FIELDS

table_metrics_table = Table(
    "table_metrics",
    metadata,
    Column("table_uuid", String, primary_key=True),
    Column("observed_at", UtcDateTime, nullable=False),
    *(Column(name, BigInteger, nullable=False) for name in TABLE_METRIC_COUNT_FIELDS),
)
