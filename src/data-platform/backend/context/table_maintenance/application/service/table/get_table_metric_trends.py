"""Define the GetTableMetricTrendsService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS, MetricTimeRange
from context.table_maintenance.application.domain.service.table import derive_metric_trend_values
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    GetTableMetricTrendsUseCase,
    GetTableMetricTrendsUseCaseInput,
    GetTableMetricTrendsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import ReadTableMetricHistoryGatewayInput

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetricHistoryGateway,
        TablesRepo,
    )


class GetTableMetricTrendsService(GetTableMetricTrendsUseCase):
    """Get a known table's metric trend from the metric history."""

    def __init__(self, tables_repo: TablesRepo, metric_history: ReadTableMetricHistoryGateway) -> None:
        """Bind the tables repo, which says which tables exist, and the metric history gateway."""
        self._tables_repo = tables_repo
        self._metric_history = metric_history

    def execute(self, request: GetTableMetricTrendsUseCaseInput) -> GetTableMetricTrendsUseCaseOutput:
        """Return one point per step of the range, ending at ``now`` rounded down to a step.

        The history is asked only for a table the repo knows. A key it has no data for is None in every point.
        A known table that is not managed is still read, so it can show its stale series for up to the history's
        6 h retention, while its current metrics are null.
        """
        try:
            time_range = MetricTimeRange(request.time_range)
        except ValueError:
            allowed = ", ".join(r.value for r in MetricTimeRange)
            raise ValidationError(f"unknown range {request.time_range}; use one of {allowed}") from None
        if self._tables_repo.get(TableId(request.uuid)) is None:
            raise NotFoundError(f"table {request.uuid} not found")
        step_seconds = int(time_range.step.total_seconds())
        end_seconds = request.now.timestamp() // step_seconds * step_seconds
        start_seconds = end_seconds - time_range.duration.total_seconds()
        history = self._metric_history.read(
            ReadTableMetricHistoryGatewayInput(
                table_uuid=request.uuid,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                step_seconds=step_seconds,
            )
        )
        points = tuple(
            GetTableMetricTrendsUseCaseOutput.Point(
                at=datetime.fromtimestamp(timestamp, UTC),
                values=derive_metric_trend_values(
                    {
                        field: history.series[field][index] if field in history.series else None
                        for field in TABLE_METRIC_COUNT_FIELDS
                    }
                ),
            )
            for index, timestamp in enumerate(history.timestamps)
        )
        return GetTableMetricTrendsUseCaseOutput(
            time_range=time_range.value,
            step_seconds=step_seconds,
            start=datetime.fromtimestamp(start_seconds, UTC),
            end=datetime.fromtimestamp(end_seconds, UTC),
            points=points,
        )
