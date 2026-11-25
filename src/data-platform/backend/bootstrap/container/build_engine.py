"""Provide the build_engine function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from bootstrap.configs import DatabaseBackend

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from bootstrap.configs import DatabaseSettings

_IN_MEMORY = ":memory:"


def build_engine(database: DatabaseSettings) -> Engine:
    """Create the SQLAlchemy engine of the configured backend, without connecting.

    The SQLite engine allows use from several threads, because the API and the
    worker call repositories from thread pools; ``:memory:`` shares one database
    through a single static connection.
    """
    if database.backend is DatabaseBackend.SQLITE:
        path = database.sqlite.path
        connect_args = {"check_same_thread": False}
        if path == _IN_MEMORY:
            return create_engine("sqlite://", connect_args=connect_args, poolclass=StaticPool)
        return create_engine(f"sqlite:///{path}", connect_args=connect_args)
    url = database.postgres.db_url.get_secret_value()
    if not url:
        msg = "GLAC_DATABASE__POSTGRES__DB_URL is required for the postgres database backend"
        raise ValueError(msg)
    return create_engine(url, pool_size=database.postgres.pool_size, pool_pre_ping=True)
