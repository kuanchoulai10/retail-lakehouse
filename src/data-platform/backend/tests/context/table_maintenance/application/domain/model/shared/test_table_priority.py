"""Test the priorities a table can have."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TablePriority


def test_default_is_p3() -> None:
    """A table with no priority set runs at the lowest one, P3."""
    assert TablePriority.default() is TablePriority.P3


def test_values_are_p0_to_p3() -> None:
    """The priorities are P0 (most urgent) to P3, in that order."""
    assert [p.value for p in TablePriority] == ["P0", "P1", "P2", "P3"]
