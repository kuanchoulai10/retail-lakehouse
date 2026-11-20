"""Define the ReadTableMetricHistoryGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadTableMetricHistoryGatewayOutput:
    """Carry the points of a window and, per metric count field, a value for each point.

    ``timestamps`` run from the window's start to its end by the step. ``series`` is keyed by the metric
    count field names, each list aligned with ``timestamps`` and holding None where there is no value;
    a field without a key has no data at all.
    """

    timestamps: list[float]
    series: dict[str, list[float | None]]
