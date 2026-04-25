"""Define the domain_event_outbox SQLAlchemy table schema."""

from sqlalchemy import Column, DateTime, String, Table

from core.adapter.outbound.sql.metadata import metadata

outbox_table = Table(
    "domain_event_outbox",
    metadata,
    Column("id", String, primary_key=True),
    Column("aggregate_type", String, nullable=False),
    Column("aggregate_id", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("payload", String, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
)
