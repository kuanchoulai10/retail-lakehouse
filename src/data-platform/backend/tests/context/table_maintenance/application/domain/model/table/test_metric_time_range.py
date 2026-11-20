"""Test the MetricTimeRange value."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.table import MetricTimeRange


def test_every_range_has_120_steps() -> None:
    """Each range holds 120 steps, so a chart has 121 points whatever the range."""
    for time_range in MetricTimeRange:
        assert time_range.duration / time_range.step == 120


@pytest.mark.parametrize(
    ("value", "duration", "step"),
    [
        ("1h", timedelta(hours=1), timedelta(seconds=30)),
        ("3h", timedelta(hours=3), timedelta(seconds=90)),
        ("6h", timedelta(hours=6), timedelta(seconds=180)),
    ],
)
def test_range_values_durations_and_steps(value: str, duration: timedelta, step: timedelta) -> None:
    """A range is named by its value and carries its duration and step."""
    time_range = MetricTimeRange(value)

    assert time_range.duration == duration
    assert time_range.step == step


def test_the_default_is_six_hours() -> None:
    """Without a range the trends show six hours."""
    assert MetricTimeRange.default() is MetricTimeRange.SIX_HOURS


def test_an_unknown_range_is_refused() -> None:
    """Only 1h, 3h and 6h are ranges."""
    with pytest.raises(ValueError, match="7d"):
        MetricTimeRange("7d")
