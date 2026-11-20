"""Define the ReadTableMetricHistoryGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table.read_table_metric_history.input import (
        ReadTableMetricHistoryGatewayInput,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metric_history.output import (
        ReadTableMetricHistoryGatewayOutput,
    )


class ReadTableMetricHistoryGateway(Gateway):
    """Read how a table's metrics changed over a window, from wherever the metrics are kept over time."""

    @abstractmethod
    def read(
        self,
        input: ReadTableMetricHistoryGatewayInput,  # noqa: A002
    ) -> ReadTableMetricHistoryGatewayOutput:
        """Return the table's metric series on the window's grid.

        Raise ``MetricHistoryUnavailableError`` when the history cannot be read.
        """
