"""Tests for the TableChange enum."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableChange


def test_table_change_values():
    """The table change enum has exactly the documented members in their documented order."""
    assert [c.value for c in TableChange] == [
        "updated",
        "settings_changed",
        "paused",
        "resumed",
        "stopped",
        "maintenance_requested",
        "reconcile_requested",
    ]
