"""Test the Measurement value object."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import (
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
)


def test_measurement_met_and_context():
    """A measurement is met by its comparison; without a threshold it is context only."""
    assert (
        Measurement(
            key="x", observed=5, unit=MeasurementUnit.COUNT, threshold=5, comparison=MeasurementComparison.AT_LEAST
        ).met
        is True
    )
    assert (
        Measurement(
            key="x", observed=5, unit=MeasurementUnit.COUNT, threshold=5, comparison=MeasurementComparison.MORE_THAN
        ).met
        is False
    )
    assert Measurement(key="x", observed=5, unit=MeasurementUnit.BYTES).met is None


def test_threshold_without_comparison_is_rejected():
    """A threshold needs a comparison."""
    with pytest.raises(ValidationError, match="comparison"):
        Measurement(key="x", observed=5, unit=MeasurementUnit.COUNT, threshold=5)


def test_comparison_without_threshold_is_rejected():
    """A comparison needs a threshold."""
    with pytest.raises(ValidationError, match="threshold"):
        Measurement(key="x", observed=5, unit=MeasurementUnit.COUNT, comparison=MeasurementComparison.AT_LEAST)


def test_measurement_is_immutable():
    """A measurement cannot be changed after construction."""
    measurement = Measurement(key="x", observed=5, unit=MeasurementUnit.COUNT)
    with pytest.raises(ValidationError):
        measurement.observed = 6


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
    assert (
        Measurement(key="x", observed=5, unit=MeasurementUnit.COUNT, threshold=5, comparison=comparison).met is expected
    )
