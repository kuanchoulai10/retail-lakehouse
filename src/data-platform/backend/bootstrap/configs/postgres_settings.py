"""Define the PostgresSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel, SecretStr


class PostgresSettings(BaseModel):
    """PostgreSQL connection and pool configuration.

    ``db_url`` is a SQLAlchemy URL with the psycopg 3 driver, such as
    ``postgresql+psycopg://user:password@host:5432/db``; it holds the password, so
    it is a secret.
    """

    db_url: SecretStr = SecretStr("")
    pool_size: int = 5
