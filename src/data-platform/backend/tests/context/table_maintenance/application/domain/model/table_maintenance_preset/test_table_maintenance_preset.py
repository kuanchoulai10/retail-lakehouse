"""Test the TableMaintenancePreset aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
    TableMaintenancePresetId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make() -> TableMaintenancePreset:
    """Build a preset named default."""
    return TableMaintenancePreset.create(
        id=TableMaintenancePresetId("t1"),
        name="default",
        settings=MaintenanceSettings(),
        now=T0,
    )


def test_create():
    """A new preset has its id, name and creation time."""
    t = make()
    assert t.id == TableMaintenancePresetId("t1")
    assert t.name == "default"
    assert t.created_at == T0
    assert t.updated_at == T0


def test_rename_and_update_settings():
    """Renaming and updating settings change them and stamp the update time."""
    t = make()
    t.rename("other", T1)
    assert t.name == "other"
    assert t.updated_at == T1
    new = MaintenanceSettings(reconcile_interval=timedelta(hours=2))
    t.update_settings(new, T1 + timedelta(hours=1))
    assert t.settings == new
    assert t.updated_at == T1 + timedelta(hours=1)
    assert t.created_at == T0
