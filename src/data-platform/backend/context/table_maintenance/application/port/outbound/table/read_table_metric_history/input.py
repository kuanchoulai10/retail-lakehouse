"""Define the ReadTableMetricHistoryGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadTableMetricHistoryGatewayInput:
    """Name the table and the window, as Unix seconds, and the seconds between two points."""

    table_uuid: str
    start_seconds: float
    end_seconds: float
    step_seconds: int
