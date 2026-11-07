"""Test the maintenance settings dict conversion functions."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    CompactionScope,
    MaintenanceSettings,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.service.shared import (
    maintenance_settings_from_dict,
    maintenance_settings_to_dict,
)


def test_empty_dict_yields_defaults():
    """An empty dict converts to the default settings."""
    assert maintenance_settings_from_dict({}) == MaintenanceSettings()


def test_partial_dict_overrides_only_given_fields():
    """A partial dict overrides only the fields it names."""
    settings = maintenance_settings_from_dict(
        {
            "reconcile_interval_seconds": 7200,
            "rewrite_data_files": {"scope": "table", "min_reducible_files": 9},
            "expire_snapshots": {"older_than_seconds": 3600, "enabled": False},
        }
    )
    assert settings.reconcile_interval == timedelta(hours=2)
    assert settings.rewrite_data_files.scope == CompactionScope.TABLE
    assert settings.rewrite_data_files.min_reducible_files == 9
    assert settings.expire_snapshots.older_than == timedelta(hours=1)
    assert settings.expire_snapshots.enabled is False
    assert settings.remove_orphan_files == MaintenanceSettings().remove_orphan_files


def test_round_trip():
    """Settings converted to a dict and back are unchanged."""
    settings = maintenance_settings_from_dict(
        {
            "rewrite_data_files": {"target_file_size_bytes": 1024},
            "rewrite_manifests": {"small_manifest_bytes": 2048},
        }
    )
    assert maintenance_settings_from_dict(maintenance_settings_to_dict(settings)) == (settings)


def test_to_dict_shape():
    """The dict form uses whole seconds for durations and nests the operation settings."""
    data = maintenance_settings_to_dict(MaintenanceSettings())
    assert data["reconcile_interval_seconds"] == 3600
    assert data["rewrite_data_files"] == {
        "enabled": True,
        "min_interval_seconds": 3600,
        "scope": "partition",
        "target_file_size_bytes": None,
        "min_reducible_files": 5,
    }
    assert data["remove_orphan_files"]["older_than_seconds"] == 3 * 86400


@pytest.mark.parametrize(
    "data",
    [
        {"unknown": 1},
        {"rewrite_data_files": {"bogus": 1}},
        {"rewrite_data_files": "nope"},
        {"rewrite_data_files": {"scope": "galaxy"}},
        {"reconcile_interval_seconds": 0},
        {"reconcile_interval_seconds": "soon"},
        {"remove_orphan_files": {"older_than_seconds": 60}},
        {"expire_snapshots": {"enabled": "yes"}},
    ],
)
def test_invalid_input_raises_validation_error(data: dict):
    """Invalid input raises a ValidationError."""
    with pytest.raises(ValidationError):
        maintenance_settings_from_dict(data)
