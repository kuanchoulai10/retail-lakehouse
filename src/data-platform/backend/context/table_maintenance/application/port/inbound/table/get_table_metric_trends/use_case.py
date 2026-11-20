"""Define the GetTableMetricTrendsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.get_table_metric_trends.input import (
    GetTableMetricTrendsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.get_table_metric_trends.output import (
    GetTableMetricTrendsUseCaseOutput,
)


class GetTableMetricTrendsUseCase(UseCase[GetTableMetricTrendsUseCaseInput, GetTableMetricTrendsUseCaseOutput]):
    """Get how one table's metrics changed over a recent window.

    Any table maintenance knows is read, managed or not. One that is not managed any more can still have
    stale series in the history, for up to its 6 h retention, unlike its current metrics, which are null.
    """

    @abstractmethod
    def execute(self, request: GetTableMetricTrendsUseCaseInput) -> GetTableMetricTrendsUseCaseOutput:
        """Get the trend, or raise NotFoundError for an unknown table and ValidationError for an unknown range."""
