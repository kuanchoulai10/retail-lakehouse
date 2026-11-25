"""Test that waiting for the schema polls until it is ready and creates nothing."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from bootstrap.container import build_engine, run_migrations, wait_for_schema
from tests.bootstrap.container.container_support import sqlite_settings

if TYPE_CHECKING:
    import pytest


def test_wait_for_schema_polls_until_ready(monkeypatch: pytest.MonkeyPatch):
    """It sleeps between checks and returns on the first ready one."""
    answers = iter([False, False, True])
    monkeypatch.setattr(
        importlib.import_module("bootstrap.container.wait_for_schema"), "schema_is_ready", lambda _engine: next(answers)
    )
    sleeps: list[float] = []

    wait_for_schema(build_engine(sqlite_settings().database), sleep=sleeps.append)

    assert sleeps == [3.0, 3.0]


def test_a_ready_schema_does_not_wait():
    """A schema that is already ready returns at once."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)
    sleeps: list[float] = []

    wait_for_schema(engine, sleep=sleeps.append)

    assert sleeps == []
