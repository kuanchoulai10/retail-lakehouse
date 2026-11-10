"""Test the SQL repository of the TableMaintenancePreset aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_preset.sql import (
    TableMaintenancePresetsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def _preset(preset_id: str, name: str) -> TableMaintenancePreset:
    return TableMaintenancePreset.create(
        TableMaintenancePresetId(preset_id),
        name,
        MaintenanceSettings(reconcile_interval=timedelta(minutes=20)),
        NOW,
    )


@pytest.fixture
def repo(engine: Engine) -> TableMaintenancePresetsSqlRepo:
    """Provide the presets repository on the test engine."""
    return TableMaintenancePresetsSqlRepo(engine)


def test_roundtrip(repo: TableMaintenancePresetsSqlRepo):
    """A stored preset loads back with its name and settings."""
    original = _preset("t1", "default")
    repo.create(original)
    loaded = repo.get(TableMaintenancePresetId("t1"))
    assert loaded is not None
    assert loaded.name == "default"
    assert loaded.settings == original.settings
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW
    assert loaded.collect_events() == []


def test_get_missing_returns_none(repo: TableMaintenancePresetsSqlRepo):
    """Getting a preset that does not exist returns None."""
    assert repo.get(TableMaintenancePresetId("nope")) is None


def test_update_persists(repo: TableMaintenancePresetsSqlRepo):
    """An update persists the new name and settings."""
    preset = _preset("t1", "default")
    repo.create(preset)
    later = NOW + timedelta(days=1)
    preset.rename("renamed", later)
    preset.update_settings(MaintenanceSettings(), later)
    repo.update(preset)
    loaded = repo.get(preset.id)
    assert loaded is not None
    assert loaded.name == "renamed"
    assert loaded.settings == MaintenanceSettings()
    assert loaded.updated_at == later


def test_update_missing_raises(repo: TableMaintenancePresetsSqlRepo):
    """Updating a preset that does not exist raises LookupError."""
    with pytest.raises(LookupError):
        repo.update(_preset("ghost", "ghost"))


def test_name_is_unique(repo: TableMaintenancePresetsSqlRepo):
    """Creating a second preset with the same name raises ConflictError."""
    repo.create(_preset("t1", "default"))
    with pytest.raises(ConflictError):
        repo.create(_preset("t2", "default"))


def test_duplicate_primary_key_raises_conflict(repo: TableMaintenancePresetsSqlRepo):
    """Creating a preset with an existing id raises ConflictError."""
    repo.create(_preset("t1", "a"))
    with pytest.raises(ConflictError):
        repo.create(_preset("t1", "b"))


def test_find_by_name_exact(repo: TableMaintenancePresetsSqlRepo):
    """Finding by name matches the exact name, including its case."""
    repo.create(_preset("t1", "default"))
    found = repo.find_by_name("default")
    assert found is not None
    assert found.id == TableMaintenancePresetId("t1")
    assert repo.find_by_name("Default") is None
    assert repo.find_by_name("defaul") is None


def test_delete(repo: TableMaintenancePresetsSqlRepo):
    """A deleted preset can no longer be loaded."""
    repo.create(_preset("t1", "default"))
    repo.delete(TableMaintenancePresetId("t1"))
    assert repo.get(TableMaintenancePresetId("t1")) is None


def test_list_all_ordered_by_name(repo: TableMaintenancePresetsSqlRepo):
    """Listing orders presets by name."""
    repo.create(_preset("1", "zeta"))
    repo.create(_preset("2", "alpha"))
    repo.create(_preset("3", "mid"))
    assert [t.name for t in repo.list_all()] == ["alpha", "mid", "zeta"]


def test_roundtrip_reads_an_equal_aggregate(repo: TableMaintenancePresetsSqlRepo):
    """A stored row reads back with the same dump and the same field types."""
    original = _preset("t1", "default")
    repo.create(original)
    loaded = repo.get(TableMaintenancePresetId("t1"))
    assert loaded is not None
    assert loaded.model_dump() == original.model_dump()
    assert {k: type(v) for k, v in loaded.model_dump().items()} == {
        k: type(v) for k, v in original.model_dump().items()
    }
