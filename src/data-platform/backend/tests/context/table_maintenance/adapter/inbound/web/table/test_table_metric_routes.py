"""Test the table current metrics route with a stub use case."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableCurrentMetricsUseCaseInput,
    GetTableCurrentMetricsUseCaseOutput,
)
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
