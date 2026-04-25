"""Provide the build_engine factory function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from core.configs import DatabaseBackend

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from core.configs import AppSettings


def build_engine(settings: AppSettings) -> Engine:
    """Create a SQLAlchemy engine from the given backend and settings."""
    if settings.database_backend == DatabaseBackend.SQLITE:
        return create_engine(f"sqlite:///{settings.sqlite.db_path}")
    if settings.database_backend == DatabaseBackend.POSTGRES:
        return create_engine(
            settings.postgres.db_url,
            pool_size=settings.postgres.pool_size,
        )
    raise ValueError(f"Unsupported database backend: {settings.database_backend!r}")
