"""Shared fixtures for SQL infrastructure tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine

from core.adapter.outbound.sql.metadata import metadata


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    """Provide an in-memory SQLite engine with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
