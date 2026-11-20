"""Define the GetTableCurrentMetricsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.get_table_current_metrics.input import (
    GetTableCurrentMetricsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.get_table_current_metrics.output import (
    GetTableCurrentMetricsUseCaseOutput,
)


class GetTableCurrentMetricsUseCase(UseCase[GetTableCurrentMetricsUseCaseInput, GetTableCurrentMetricsUseCaseOutput]):
    """Get the newest metrics of one table."""

    @abstractmethod
    def execute(self, request: GetTableCurrentMetricsUseCaseInput) -> GetTableCurrentMetricsUseCaseOutput:
        """Get the newest metrics of one table, or raise NotFoundError for an unknown table."""
