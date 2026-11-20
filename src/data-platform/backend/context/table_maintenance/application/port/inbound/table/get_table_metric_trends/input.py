"""Define the GetTableMetricTrendsUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class GetTableMetricTrendsUseCaseInput(UseCaseInput):
    """Carry the request for a table's metric trend.

    ``time_range`` is ``1h``, ``3h`` or ``6h``; ``now`` is the moment the window ends at, before it is
    rounded down to a step.
    """

    uuid: str
    time_range: str
    now: datetime
