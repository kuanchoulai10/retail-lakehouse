from unittest.mock import patch

import pytest
from sqlalchemy import Engine

from adapter.outbound.sql.engine_factory import build_engine
from configs import AppSettings, JobsRepoBackend


def test_sqlite_backend_builds_sqlite_engine():
    settings = AppSettings()
    settings.sqlite.db_path = ":memory:"
    engine = build_engine(JobsRepoBackend.SQLITE, settings)
    assert isinstance(engine, Engine)
    assert engine.dialect.name == "sqlite"


def test_postgres_backend_delegates_to_create_engine():
    settings = AppSettings()
    settings.postgres.db_url = "postgresql+psycopg://user:pass@host/db"
    settings.postgres.pool_size = 7
    with patch("adapter.outbound.sql.engine_factory.create_engine") as mock_create:
        build_engine(JobsRepoBackend.POSTGRES, settings)
    call = mock_create.call_args
    assert call.args[0] == "postgresql+psycopg://user:pass@host/db"
    assert call.kwargs.get("pool_size") == 7


def test_in_memory_backend_is_not_supported():
    settings = AppSettings()
    with pytest.raises(ValueError, match="IN_MEMORY"):
        build_engine(JobsRepoBackend.IN_MEMORY, settings)
