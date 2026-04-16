from __future__ import annotations

from pydantic import BaseModel


class SqliteSettings(BaseModel):
    db_path: str = ":memory:"
