"""Define the GetTableMetricTrendsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableMetricTrendsUseCaseOutput(UseCaseOutput):
    """Carry a table's metric trend: one point per step from ``start`` to ``end`` inclusive."""

    class Point(UseCaseOutput):
        """One moment of the trend; ``values`` holds every trend key, None where there is no value."""

        at: datetime
        values: dict[str, float | None]

    time_range: str
    step_seconds: int
    start: datetime
    end: datetime
    points: tuple[Point, ...]
