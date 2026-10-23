"""Define the SqliteSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class SqliteSettings(BaseModel):
    """SQLite configuration for local and development use.

    ``path`` is the database file; ``:memory:`` keeps one in-memory database shared
    by every connection of the engine.
    """

    path: str = "table-maintenance.db"
