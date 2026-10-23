from __future__ import annotations

from adapter.outbound.sql.engine_factory import build_engine
from bootstrap.configs import AppSettings, PostgresSettings


def test_build_engine_enables_pool_pre_ping_without_connecting():
    settings = AppSettings(
        postgres=PostgresSettings(
            db_url="postgresql+psycopg://u:p@localhost:1/db", pool_size=3
        )
    )
    engine = build_engine(settings)
    assert engine.pool._pre_ping is True
