from sqlalchemy import JSON, Boolean, Column, DateTime, String, Table

from adapter.outbound.sql.metadata import metadata

jobs_table = Table(
    "jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("job_type", String, nullable=False),
    Column("catalog", String, nullable=False, default=""),
    Column("table", String, nullable=False, default=""),
    Column("job_config", JSON, nullable=False, default=dict),
    Column("cron", String, nullable=True),
    Column("enabled", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
