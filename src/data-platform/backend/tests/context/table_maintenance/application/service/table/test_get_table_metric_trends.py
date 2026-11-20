"""Test the GetTableMetricTrendsService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.table import (
    TABLE_METRIC_COUNT_FIELDS,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import GetTableMetricTrendsUseCaseInput
from context.table_maintenance.application.port.outbound.table import MetricHistoryUnavailableError
from context.table_maintenance.application.service.table import GetTableMetricTrendsService
from tests.context.table_maintenance.fakes.scripted_read_table_metric_history_gateway import (
    ScriptedReadTableMetricHistoryGateway,
)

RULE_1 = "dr-00000000000000000000000001"
TREND_KEYS = {*TABLE_METRIC_COUNT_FIELDS, "manifest_average_size_bytes", "manifest_average_entries"}
AT = datetime(2026, 11, 20, 12, 0, 47, tzinfo=UTC)


@pytest.fixture
def history() -> ScriptedReadTableMetricHistoryGateway:
    """Provide a metric history gateway that serves what the test scripts."""
    return ScriptedReadTableMetricHistoryGateway()


def _register(tables_repo, now, uuid="u-1"):
    tables_repo.create(
        Table.register(
            TableId(uuid),
            TableName(catalog="iceberg", namespace="retail", table="orders"),
            TableDiscoveryRuleId(RULE_1),
            now,
        )
    )


def _service(tables_repo, history):
    return GetTableMetricTrendsService(tables_repo, history)


def _request(time_range="1h", uuid="u-1"):
    return GetTableMetricTrendsUseCaseInput(uuid=uuid, time_range=time_range, now=AT)


def test_trends_window_ends_on_a_step(tables_repo, history, now):
    """Now 12:00:47 on a 1h range ends at 12:00:30 and starts an hour before, with 121 points."""
    _register(tables_repo, now)

    output = _service(tables_repo, history).execute(_request())

    assert output.time_range == "1h"
    assert output.step_seconds == 30
    assert output.end == datetime(2026, 11, 20, 12, 0, 30, tzinfo=UTC)
    assert output.start == datetime(2026, 11, 20, 11, 0, 30, tzinfo=UTC)
    assert len(output.points) == 121
    assert output.points[0].at == output.start
    assert output.points[-1].at == output.end
    assert history.calls[0].table_uuid == "u-1"
    assert history.calls[0].step_seconds == 30
    assert history.calls[0].end_seconds == output.end.timestamp()
    assert history.calls[0].start_seconds == output.start.timestamp()


@pytest.mark.parametrize(("time_range", "step"), [("1h", 30), ("3h", 90), ("6h", 180)])
def test_every_range_has_121_points_on_its_step(tables_repo, history, now, time_range, step):
    """Each range answers 121 points, one per step, ending on a multiple of the step."""
    _register(tables_repo, now)

    output = _service(tables_repo, history).execute(_request(time_range))

    assert output.step_seconds == step
    assert len(output.points) == 121
    assert (output.points[1].at - output.points[0].at).total_seconds() == step
    assert output.end.timestamp() % step == 0


def test_every_point_carries_every_trend_key(tables_repo, history, now):
    """A key Prometheus has no series for is null in every point, and the two averages are present."""
    _register(tables_repo, now)

    output = _service(tables_repo, history).execute(_request())

    assert all(set(point.values) == TREND_KEYS for point in output.points)
    assert all(value is None for point in output.points for value in point.values.values())


def test_points_carry_the_series_and_the_derived_averages(tables_repo, history, now):
    """The values come from the gateway by position, and the averages are derived per point."""
    _register(tables_repo, now)
    count = 121
    history.series = {
        "data_files": [float(index) for index in range(count)],
        "manifests": [4.0] * count,
        "manifests_size_bytes": [400.0] * count,
        "manifest_added_entries": [6.0] * count,
        "manifest_existing_entries": [2.0] * count,
        "manifest_deleted_entries": [0.0] * count,
    }

    output = _service(tables_repo, history).execute(_request())

    assert [point.values["data_files"] for point in output.points[:3]] == [0.0, 1.0, 2.0]
    assert output.points[5].values["manifest_average_size_bytes"] == 100
    assert output.points[5].values["manifest_average_entries"] == 2


def test_trends_of_unknown_table_is_not_found(tables_repo, history):
    """An unknown uuid is a NotFoundError and Prometheus is never asked."""
    with pytest.raises(NotFoundError):
        _service(tables_repo, history).execute(_request(uuid="u-nope"))

    assert history.calls == []


def test_an_unknown_range_is_a_validation_error(tables_repo, history, now):
    """Anything but 1h, 3h and 6h is refused."""
    _register(tables_repo, now)

    with pytest.raises(ValidationError, match="7d"):
        _service(tables_repo, history).execute(_request("7d"))

    assert history.calls == []


def test_an_unavailable_history_propagates(tables_repo, history, now):
    """The use case lets the gateway's error through for the web layer to answer 502."""
    _register(tables_repo, now)
    history.error = MetricHistoryUnavailableError("prometheus is down")

    with pytest.raises(MetricHistoryUnavailableError, match="prometheus is down"):
        _service(tables_repo, history).execute(_request())
