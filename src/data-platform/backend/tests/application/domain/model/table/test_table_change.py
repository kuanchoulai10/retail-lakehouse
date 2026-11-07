"""Tests for the TableChange enum."""

from __future__ import annotations

from application.domain.model.table import TableChange


def test_table_change_values():
    assert [c.value for c in TableChange] == [
        "updated",
        "settings_changed",
        "paused",
        "resumed",
        "stopped",
        "maintenance_requested",
    ]
