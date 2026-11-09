"""Test the Measurement value object."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
)


def test_measurement_met_and_context():
    """A measurement is met by its comparison; without a threshold it is context only."""
    assert Measurement("x", 5, MeasurementUnit.COUNT, 5, MeasurementComparison.AT_LEAST).met is True
    assert Measurement("x", 5, MeasurementUnit.COUNT, 5, MeasurementComparison.MORE_THAN).met is False
    assert Measurement("x", 5, MeasurementUnit.BYTES).met is None


def test_measurement_rejects_threshold_without_comparison():
    """A threshold needs a comparison."""
    with pytest.raises(ValueError, match="comparison"):
        Measurement("x", 5, MeasurementUnit.COUNT, 5)


def test_measurement_rejects_comparison_without_threshold():
    """A comparison needs a threshold."""
    with pytest.raises(ValueError, match="threshold"):
        Measurement("x", 5, MeasurementUnit.COUNT, None, MeasurementComparison.AT_LEAST)


@pytest.mark.parametrize(
    ("comparison", "expected"),
    [
        (MeasurementComparison.AT_LEAST, True),
        (MeasurementComparison.MORE_THAN, False),
        (MeasurementComparison.LESS_THAN, False),
        (MeasurementComparison.AT_MOST, True),
    ],
)
def test_measurement_comparisons_at_the_threshold(comparison, expected):
    """Each comparison is evaluated against the threshold."""
    assert Measurement("x", 5, MeasurementUnit.COUNT, 5, comparison).met is expected
