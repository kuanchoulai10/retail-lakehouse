"""Test the compute sizes a maintenance attempt runs at."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import ComputeSize


def test_sizes_step_up_and_down() -> None:
    """Each size knows the next larger and smaller size, with none past the ends."""
    assert ComputeSize.S.larger() is ComputeSize.M
    assert ComputeSize.M.larger() is ComputeSize.L
    assert ComputeSize.L.larger() is None
    assert ComputeSize.S.smaller() is None
    assert ComputeSize.M.smaller() is ComputeSize.S
    assert ComputeSize.L.smaller() is ComputeSize.M


def test_size_values_are_the_wire_names() -> None:
    """The size values are S, M and L."""
    assert [size.value for size in ComputeSize] == ["S", "M", "L"]
