"""Define the SqliteSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class SqliteSettings(BaseModel):
    """SQLite database path configuration."""

    db_path: str = ":memory:"
