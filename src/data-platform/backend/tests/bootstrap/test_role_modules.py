"""Test that the role modules import cleanly and that a role's main runs on the settings it is given."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, inspect

from bootstrap import migrate
from bootstrap.configs import MigrateSettings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "module",
    [
        "bootstrap.api",
        "bootstrap.worker",
        "bootstrap.event_consumer",
        "bootstrap.migrate",
    ],
)
def test_component_modules_import_without_side_effects(module: str):
    """Each component module imports without running anything and exposes a callable main."""
    loaded = importlib.import_module(module)

    assert callable(loaded.main)


def test_migrate_runs_on_the_settings_it_is_given(tmp_path: Path):
    """The migrate role builds its database from the settings passed in, not from a global."""
    path = tmp_path / "tm.db"

    migrate.main(MigrateSettings.model_validate({"database": {"backend": "sqlite", "sqlite": {"path": str(path)}}}))

    assert "table_maintenance_policies" in inspect(create_engine(f"sqlite:///{path}")).get_table_names()
