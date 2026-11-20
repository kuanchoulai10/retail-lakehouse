"""Define the GetTableCurrentMetricsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableCurrentMetricsUseCaseInput(UseCaseInput):
    """Carry the request to get the newest metrics of one table."""

    uuid: str
