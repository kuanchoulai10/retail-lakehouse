"""Define the ScriptedReadTableMetricHistoryGateway fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetricHistoryGateway,
    ReadTableMetricHistoryGatewayOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetricHistoryGatewayInput


class ScriptedReadTableMetricHistoryGateway(ReadTableMetricHistoryGateway):
    """Serve the series configured per field on the asked window, record each read and fail when told."""

    def __init__(self) -> None:
        """Start with no series and no failure."""
        self.series: dict[str, list[float | None]] = {}
        self.calls: list[ReadTableMetricHistoryGatewayInput] = []
        self.error: Exception | None = None

    def read(
        self,
        input: ReadTableMetricHistoryGatewayInput,  # noqa: A002
    ) -> ReadTableMetricHistoryGatewayOutput:
        """Return the configured series on the asked grid; raise the configured error first."""
        self.calls.append(input)
        if self.error is not None:
            raise self.error
        count = round((input.end_seconds - input.start_seconds) / input.step_seconds) + 1
        timestamps = [input.start_seconds + index * input.step_seconds for index in range(count)]
        return ReadTableMetricHistoryGatewayOutput(
            timestamps=timestamps,
            series={field: values[:count] for field, values in self.series.items()},
        )
