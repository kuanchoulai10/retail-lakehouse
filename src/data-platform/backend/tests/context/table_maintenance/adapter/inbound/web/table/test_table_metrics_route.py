"""Test the table metrics exposition route with a stub use case."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseOutput
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)


def test_route_serves_text_plain() -> None:
    """The route answers 200 in the Prometheus text format."""
    client = build_client(list_table_metrics=StubUseCase(ListTableMetricsUseCaseOutput(tables=())))

    response = client.get("/v1/table-metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "# TYPE iceberg_table_info gauge" in response.text


def test_route_is_not_in_openapi() -> None:
    """Prometheus is the only caller, so the route stays out of the schema."""
    client = build_client(list_table_metrics=StubUseCase(ListTableMetricsUseCaseOutput(tables=())))

    assert "/v1/table-metrics" not in client.get("/openapi.json").json()["paths"]
