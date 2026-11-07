"""Test the SQLAlchemy engine builder for Postgres and SQLite."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from pydantic import SecretStr
from sqlalchemy import inspect

from bootstrap.configs import (
    AppSettings,
    DatabaseBackend,
    PostgresSettings,
    SqliteSettings,
)
from bootstrap.container import build_engine
from context.table_maintenance.adapter.outbound.shared.sql import create_schema

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.pool import QueuePool


def test_postgres_engine_enables_pool_pre_ping_without_connecting():
    """The Postgres engine pre-pings pooled connections and does not connect when built."""
    settings = AppSettings(
        postgres=PostgresSettings(db_url=SecretStr("postgresql+psycopg://u:p@localhost:1/db"), pool_size=3)
    )

    engine = build_engine(settings)

    assert engine.dialect.name == "postgresql"
    pool = cast("QueuePool", engine.pool)
    assert pool._pre_ping is True  # noqa: SLF001
    assert pool.size() == 3


def test_postgres_without_url_fails_fast():
    """Building a Postgres engine without a database URL raises a ValueError naming the setting."""
    with pytest.raises(ValueError, match="GLAC_POSTGRES__DB_URL"):
        build_engine(AppSettings())


def test_sqlite_in_memory_engine_shares_one_database():
    """An in-memory SQLite engine shares one database and creates the schema."""
    settings = AppSettings(database_backend=DatabaseBackend.SQLITE, sqlite=SqliteSettings(path=":memory:"))

    engine = build_engine(settings)
    create_schema(engine)

    assert "table_maintenance_presets" in inspect(engine).get_table_names()


def test_sqlite_file_engine(tmp_path: Path):
    """A file-backed SQLite engine creates the database file."""
    path = tmp_path / "tm.db"
    settings = AppSettings(database_backend=DatabaseBackend.SQLITE, sqlite=SqliteSettings(path=str(path)))

    create_schema(build_engine(settings))

    assert path.exists()
