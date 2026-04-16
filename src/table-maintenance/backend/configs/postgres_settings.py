from __future__ import annotations

from pydantic import BaseModel


class PostgresSettings(BaseModel):
    db_url: str = ""
    pool_size: int = 5
