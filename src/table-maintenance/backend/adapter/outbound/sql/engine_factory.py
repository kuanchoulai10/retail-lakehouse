"""Provide the build_engine factory function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from bootstrap.configs import AppSettings


def build_engine(settings: AppSettings) -> Engine:
    """Create a PostgreSQL SQLAlchemy engine from the application settings."""
    return create_engine(
        settings.postgres.db_url,
        pool_size=settings.postgres.pool_size,
        pool_pre_ping=True,
    )
