"""Test that the migrate role creates the schema, or with ``wait`` only waits for it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, inspect

from bootstrap import migrate
from bootstrap.configs import MigrateSettings

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _settings(path: Path) -> MigrateSettings:
    return MigrateSettings.model_validate({"database": {"backend": "sqlite", "sqlite": {"path": str(path)}}})


def test_migrate_creates_the_schema(tmp_path: Path):
    """Without ``wait`` the role creates the tables."""
    path = tmp_path / "tm.db"

    migrate.main(_settings(path))

    assert "table_maintenance_policies" in inspect(create_engine(f"sqlite:///{path}")).get_table_names()


def test_migrate_wait_creates_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """With ``wait`` the role waits on the database it is given and creates no table."""
    path = tmp_path / "tm.db"
    waited: list[Any] = []
    monkeypatch.setattr(migrate, "wait_for_schema", waited.append)

    migrate.main(_settings(path), wait=True)

    assert len(waited) == 1
    assert inspect(create_engine(f"sqlite:///{path}")).get_table_names() == []
