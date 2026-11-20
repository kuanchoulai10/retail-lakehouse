"""Test the table current metrics route with a stub use case."""

from __future__ import annotations

from datetime import timedelta

from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableCurrentMetricsUseCaseInput,
    GetTableCurrentMetricsUseCaseOutput,
    GetTableMetricTrendsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import MetricHistoryUnavailableError
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)


def test_current_metrics_returns_the_counts() -> None:
    """The route answers 200 with the observation time and every count."""
    counts = {field: index for index, field in enumerate(TABLE_METRIC_COUNT_FIELDS, start=1)}
    stub = StubUseCase(GetTableCurrentMetricsUseCaseOutput(observed_at=NOW, counts=counts))
    client = build_client(get_table_current_metrics=stub)

    response = client.get("/v1/tables/u1/metrics/current")

    body = response.json()
    assert response.status_code == 200
    assert body["observed_at"].startswith("2026-10-24T12:00")
    assert body["metrics"] == counts
    assert body["metrics"]["data_files"] == 1
    assert stub.requests == [GetTableCurrentMetricsUseCaseInput(uuid="u1")]


def test_current_metrics_of_a_table_without_a_row_are_null() -> None:
    """A known table with no row answers 200 with both fields null."""
    stub = StubUseCase(GetTableCurrentMetricsUseCaseOutput(observed_at=None, counts=None))
    client = build_client(get_table_current_metrics=stub)

    response = client.get("/v1/tables/u1/metrics/current")

    assert response.status_code == 200
    assert response.json() == {"observed_at": None, "metrics": None}


def test_current_metrics_of_an_unknown_table_are_404() -> None:
    """An unknown table answers 404."""
    client = build_client(get_table_current_metrics=StubUseCase(error=NotFoundError("table u1 not found")))

    response = client.get("/v1/tables/u1/metrics/current")

    assert response.status_code == 404


def _trends(values: dict[str, float | None]) -> GetTableMetricTrendsUseCaseOutput:
    return GetTableMetricTrendsUseCaseOutput(
        time_range="1h",
        step_seconds=30,
        start=NOW,
        end=NOW + timedelta(seconds=30),
        points=(
            GetTableMetricTrendsUseCaseOutput.Point(at=NOW, values=values),
            GetTableMetricTrendsUseCaseOutput.Point(at=NOW + timedelta(seconds=30), values={"data_files": None}),
        ),
    )


def test_trends_return_the_points() -> None:
    """The route answers 200 with the window and each point's values, null where there is none."""
    stub = StubUseCase(_trends({"data_files": 3.0}))
    client = build_client(get_table_metric_trends=stub)

    response = client.get("/v1/tables/u1/metrics?range=1h")

    body = response.json()
    assert response.status_code == 200
    assert body["time_range"] == "1h"
    assert body["step_seconds"] == 30
    assert body["start"].startswith("2026-10-24T12:00")
    assert body["points"][0]["values"] == {"data_files": 3.0}
    assert body["points"][1]["values"] == {"data_files": None}
    assert body["points"][1]["at"].startswith("2026-10-24T12:00:30")
    request = stub.requests[0]
    assert (request.uuid, request.time_range) == ("u1", "1h")
    assert request.now.tzinfo is not None


def test_trends_default_to_six_hours() -> None:
    """Without a range the route asks for 6h."""
    stub = StubUseCase(_trends({}))
    client = build_client(get_table_metric_trends=stub)

    client.get("/v1/tables/u1/metrics")

    assert stub.requests[0].time_range == "6h"


def test_route_rejects_an_unknown_range() -> None:
    """A range other than 1h, 3h and 6h is a 422 and reaches no use case."""
    stub = StubUseCase(_trends({}))
    client = build_client(get_table_metric_trends=stub)

    response = client.get("/v1/tables/u1/metrics?range=7d")

    assert response.status_code == 422
    assert stub.requests == []


def test_trends_of_an_unknown_table_are_404() -> None:
    """An unknown table answers 404."""
    client = build_client(get_table_metric_trends=StubUseCase(error=NotFoundError("table u1 not found")))

    assert client.get("/v1/tables/u1/metrics").status_code == 404


def test_route_answers_502_when_prometheus_is_down() -> None:
    """A Prometheus that cannot answer is a 502 whose detail names the reason."""
    client = build_client(
        get_table_metric_trends=StubUseCase(error=MetricHistoryUnavailableError("Prometheus is unreachable: refused"))
    )

    response = client.get("/v1/tables/u1/metrics")

    assert response.status_code == 502
    assert "Prometheus is unreachable: refused" in response.json()["detail"]
