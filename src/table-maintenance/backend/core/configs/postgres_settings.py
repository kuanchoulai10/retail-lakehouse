"""Define the PostgresSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class PostgresSettings(BaseModel):
    """PostgreSQL connection and pool configuration."""

    db_url: str = ""
    pool_size: int = 5
