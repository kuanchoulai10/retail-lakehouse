"""Test the compute sizes a maintenance attempt runs at."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    ("size", "other", "expected"),
    [
        (ComputeSize.S, ComputeSize.L, ComputeSize.L),
        (ComputeSize.M, ComputeSize.S, ComputeSize.M),
        (ComputeSize.M, ComputeSize.M, ComputeSize.M),
    ],
)
def test_at_least_is_the_larger_of_two_sizes(size, other, expected):
    """A size raised to at least another is the larger of the two."""
    assert size.at_least(other) is expected
