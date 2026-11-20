"""Define the ListTableMetricsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.list_table_metrics.input import (
    ListTableMetricsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.list_table_metrics.output import (
    ListTableMetricsUseCaseOutput,
)


class ListTableMetricsUseCase(UseCase[ListTableMetricsUseCaseInput, ListTableMetricsUseCaseOutput]):
    """List the newest metrics of every managed table."""

    @abstractmethod
    def execute(self, request: ListTableMetricsUseCaseInput) -> ListTableMetricsUseCaseOutput:
        """List the newest metrics of every managed table, by table uuid."""
