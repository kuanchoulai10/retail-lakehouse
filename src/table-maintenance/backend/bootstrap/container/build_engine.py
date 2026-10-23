"""Provide the build_engine function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from bootstrap.configs.database_backend import DatabaseBackend

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from bootstrap.configs.app_settings import AppSettings

_IN_MEMORY = ":memory:"


def build_engine(settings: AppSettings) -> Engine:
    """Create the SQLAlchemy engine of the configured backend, without connecting.

    The SQLite engine allows use from several threads, because the API and the
    worker call repositories from thread pools; ``:memory:`` shares one database
    through a single static connection.
    """
    if settings.database_backend is DatabaseBackend.SQLITE:
        path = settings.sqlite.path
        connect_args = {"check_same_thread": False}
        if path == _IN_MEMORY:
            return create_engine(
                "sqlite://", connect_args=connect_args, poolclass=StaticPool
            )
        return create_engine(f"sqlite:///{path}", connect_args=connect_args)
    url = settings.postgres.db_url.get_secret_value()
    if not url:
        msg = "GLAC_POSTGRES__DB_URL is required for the postgres database backend"
        raise ValueError(msg)
    return create_engine(url, pool_size=settings.postgres.pool_size, pool_pre_ping=True)
