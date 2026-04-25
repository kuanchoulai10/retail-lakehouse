"""Tests for build_engine."""

from unittest.mock import patch

from sqlalchemy import Engine

from core.adapter.outbound.sql.engine_factory import build_engine
from core.configs import AppSettings, DatabaseBackend


def test_sqlite_backend_builds_sqlite_engine():
    """Verify that SQLite backend builds a SQLite engine."""
    settings = AppSettings()
    settings.database_backend = DatabaseBackend.SQLITE
    settings.sqlite.db_path = ":memory:"
    engine = build_engine(settings)
    assert isinstance(engine, Engine)
    assert engine.dialect.name == "sqlite"


def test_postgres_backend_delegates_to_create_engine():
    """Verify that Postgres backend delegates to SQLAlchemy create_engine."""
    settings = AppSettings()
    settings.database_backend = DatabaseBackend.POSTGRES
    settings.postgres.db_url = "postgresql+psycopg://user:pass@host/db"
    settings.postgres.pool_size = 7
    with patch("core.adapter.outbound.sql.engine_factory.create_engine") as mock_create:
        build_engine(settings)
    call = mock_create.call_args
    assert call.args[0] == "postgresql+psycopg://user:pass@host/db"
    assert call.kwargs.get("pool_size") == 7
