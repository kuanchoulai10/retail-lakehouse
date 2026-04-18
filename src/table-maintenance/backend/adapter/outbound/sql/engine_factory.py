from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from configs import DatabaseBackend

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from configs import AppSettings


def build_engine(settings: AppSettings) -> Engine:
    if settings.database_backend == DatabaseBackend.SQLITE:
        return create_engine(f"sqlite:///{settings.sqlite.db_path}")
    if settings.database_backend == DatabaseBackend.POSTGRES:
        return create_engine(
            settings.postgres.db_url,
            pool_size=settings.postgres.pool_size,
        )
    raise ValueError(f"Unsupported database backend: {settings.database_backend!r}")
