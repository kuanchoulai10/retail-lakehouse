"""Define the GetTableCurrentMetricsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class GetTableCurrentMetricsUseCaseOutput(UseCaseOutput):
    """Carry a table's newest metrics, or nothing when it is not managed or not reconciled yet.

    ``counts`` is keyed by the metric count field names.
    """

    observed_at: datetime | None
    counts: dict[str, int] | None
