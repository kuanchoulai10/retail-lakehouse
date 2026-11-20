"""Define the MetricTimeRange enumeration."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

_DURATIONS: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "6h": timedelta(hours=6),
}
_STEPS: dict[str, timedelta] = {
    "1h": timedelta(seconds=30),
    "3h": timedelta(seconds=90),
    "6h": timedelta(seconds=180),
}


class MetricTimeRange(StrEnum):
    """How far back a metric trend reaches; every range holds 120 steps, so a chart has 121 points."""

    ONE_HOUR = "1h"
    THREE_HOURS = "3h"
    SIX_HOURS = "6h"

    @property
    def duration(self) -> timedelta:
        """Return how long the range is."""
        return _DURATIONS[self.value]

    @property
    def step(self) -> timedelta:
        """Return the time between two points of the range."""
        return _STEPS[self.value]

    @classmethod
    def default(cls) -> MetricTimeRange:
        """Return the range shown when none is asked for."""
        return cls.SIX_HOURS
