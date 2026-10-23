"""Provide a SQLite engine with the control-plane schema."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from adapter.outbound.sql.create_schema import create_schema


@pytest.fixture
def engine() -> Engine:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_schema(eng)
    return eng
