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
    """Get how one table's metrics changed over a recent window."""

    @abstractmethod
    def execute(self, request: GetTableMetricTrendsUseCaseInput) -> GetTableMetricTrendsUseCaseOutput:
        """Get the trend, or raise NotFoundError for an unknown table and ValidationError for an unknown range."""
