"""Test the priorities a table can have."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TablePriority


def test_default_is_p3() -> None:
    """A table with no priority set runs at the lowest one, P3."""
    assert TablePriority.default() is TablePriority.P3


def test_values_are_p0_to_p3() -> None:
    """The priorities are P0 (most urgent) to P3, in that order."""
    assert [p.value for p in TablePriority] == ["P0", "P1", "P2", "P3"]


def test_p0_outranks_p3() -> None:
    """A more urgent priority outranks a less urgent one."""
    assert TablePriority.P0.outranks(TablePriority.P3)
    assert not TablePriority.P3.outranks(TablePriority.P0)


def test_equal_does_not_outrank() -> None:
    """A priority does not outrank itself."""
    assert not TablePriority.P1.outranks(TablePriority.P1)
