"""Test the ReadTableMetricHistoryPrometheusGateway against a mock Prometheus."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from context.table_maintenance.adapter.outbound.table.prometheus import ReadTableMetricHistoryPrometheusGateway
from context.table_maintenance.application.port.outbound.table import (
    MetricHistoryUnavailableError,
    ReadTableMetricHistoryGatewayInput,
)

START = 1_000_000.0
STEP = 30
END = START + 2 * STEP
INPUT = ReadTableMetricHistoryGatewayInput(table_uuid="u1", start_seconds=START, end_seconds=END, step_seconds=STEP)


def _series(name: str, values: list[tuple[float, str]], **labels: str) -> dict[str, Any]:
    return {
        "metric": {"__name__": name, "table_uuid": "u1", "job": "table-maintenance-api", **labels},
        "values": [[ts, value] for ts, value in values],
    }


def _matrix(*series: dict[str, Any]) -> dict[str, Any]:
    return {"status": "success", "data": {"resultType": "matrix", "result": list(series)}}


def _gateway(
    handler: Any,  # noqa: ANN401
) -> ReadTableMetricHistoryPrometheusGateway:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ReadTableMetricHistoryPrometheusGateway("http://prometheus:9090", client)


def _answer(body: dict[str, Any], status_code: int = 200) -> Any:  # noqa: ANN401
    return lambda _request: httpx.Response(status_code, json=body)


def test_gateway_sends_the_fixed_query() -> None:
    """One GET to query_range carries the fixed selector and the window as given."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_matrix())

    _gateway(handler).read(INPUT)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/query_range"
    assert request.url.params["query"] == '{__name__=~"iceberg_table_.+", table_uuid="u1"}'
    assert float(request.url.params["start"]) == START
    assert float(request.url.params["end"]) == END
    assert float(request.url.params["step"]) == STEP


def test_gateway_escapes_the_uuid_in_the_selector() -> None:
    """A uuid holding a quote cannot leave the string literal."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_matrix())

    _gateway(handler).read(
        ReadTableMetricHistoryGatewayInput(table_uuid='a"b', start_seconds=START, end_seconds=END, step_seconds=STEP)
    )

    assert requests[0].url.params["query"] == '{__name__=~"iceberg_table_.+", table_uuid="a\\"b"}'


def test_gateway_aligns_series_and_fills_gaps() -> None:
    """Values at the first and last step only leave a null in between."""
    body = _matrix(_series("iceberg_table_manifests", [(START, "3"), (START + 2 * STEP, "5")]))

    output = _gateway(_answer(body)).read(INPUT)

    assert output.timestamps == [START, START + STEP, START + 2 * STEP]
    assert output.series == {"manifests": [3.0, None, 5.0]}


def test_gateway_leaves_out_a_field_without_series() -> None:
    """A field Prometheus has nothing for is absent, meaning no data."""
    output = _gateway(_answer(_matrix())).read(INPUT)

    assert output.timestamps == [START, START + STEP, START + 2 * STEP]
    assert output.series == {}


def test_gateway_maps_content_and_status_labels() -> None:
    """The content and status labels pick the field of a shared metric name."""
    body = _matrix(
        _series("iceberg_table_files", [(START, "1")], content="data"),
        _series("iceberg_table_files", [(START, "2")], content="position_delete"),
        _series("iceberg_table_files", [(START, "3")], content="equality_delete"),
        _series("iceberg_table_files", [(START, "4")], content="deletion_vector"),
        _series("iceberg_table_manifest_entries", [(START, "5")], status="added"),
        _series("iceberg_table_manifest_entries", [(START, "6")], status="existing"),
        _series("iceberg_table_manifest_entries", [(START, "7")], status="deleted"),
        _series("iceberg_table_data_size_bytes", [(START, "8")]),
    )

    series = _gateway(_answer(body)).read(INPUT).series

    assert {field: values[0] for field, values in series.items()} == {
        "data_files": 1.0,
        "position_delete_files": 2.0,
        "equality_delete_files": 3.0,
        "deletion_vectors": 4.0,
        "manifest_added_entries": 5.0,
        "manifest_existing_entries": 6.0,
        "manifest_deleted_entries": 7.0,
        "data_size_bytes": 8.0,
    }


def test_gateway_ignores_info_and_observed_timestamp() -> None:
    """The names series and the observation time are not metrics of a trend."""
    body = _matrix(
        _series("iceberg_table_info", [(START, "1")], catalog="iceberg", namespace="n", table="t"),
        _series("iceberg_table_observed_timestamp_seconds", [(START, "1.7e9")]),
        _series("iceberg_table_something_new", [(START, "1")]),
    )

    assert _gateway(_answer(body)).read(INPUT).series == {}


def test_gateway_turns_nan_and_infinities_into_none() -> None:
    """Prometheus may answer NaN or an infinity; the trend shows null."""
    body = _matrix(_series("iceberg_table_snapshots", [(START, "NaN"), (START + STEP, "+Inf"), (END, "-Inf")]))

    assert _gateway(_answer(body)).read(INPUT).series == {"snapshots": [None, None, None]}


def test_gateway_takes_the_max_of_series_mapping_to_one_field() -> None:
    """Two series of one field (for example two scraped instances) give the larger value."""
    body = _matrix(
        _series("iceberg_table_snapshots", [(START, "2"), (START + STEP, "NaN")], instance="a"),
        _series("iceberg_table_snapshots", [(START, "4"), (START + STEP, "6")], instance="b"),
    )

    assert _gateway(_answer(body)).read(INPUT).series == {"snapshots": [4.0, 6.0, None]}


def test_gateway_ignores_samples_off_the_grid() -> None:
    """A sample outside the window or between steps is dropped."""
    body = _matrix(_series("iceberg_table_snapshots", [(START - STEP, "9"), (START + 10, "9"), (END + STEP, "9")]))

    assert _gateway(_answer(body)).read(INPUT).series == {"snapshots": [None, None, None]}


def test_gateway_error_status_is_unavailable() -> None:
    """A 200 answer saying status error carries Prometheus's own reason."""
    gateway = _gateway(_answer({"status": "error", "errorType": "bad_data", "error": "bad"}))

    with pytest.raises(MetricHistoryUnavailableError, match="bad"):
        gateway.read(INPUT)


def test_gateway_non_2xx_is_unavailable() -> None:
    """A 4xx answer names Prometheus's error text when it has one."""
    gateway = _gateway(_answer({"status": "error", "error": "parse error"}, status_code=400))

    with pytest.raises(MetricHistoryUnavailableError, match=r"400.*parse error"):
        gateway.read(INPUT)


def test_gateway_non_2xx_without_a_body_names_the_status() -> None:
    """An answer that is no JSON is reported by its HTTP status."""
    gateway = _gateway(lambda _request: httpx.Response(503, text="overloaded"))

    with pytest.raises(MetricHistoryUnavailableError, match="503"):
        gateway.read(INPUT)


def test_gateway_garbled_success_is_unavailable() -> None:
    """A 200 answer that is not a matrix is unavailable, not a crash."""
    for body in ({"status": "success", "data": {"resultType": "vector", "result": []}}, {"unexpected": 1}):
        with pytest.raises(MetricHistoryUnavailableError):
            _gateway(_answer(body)).read(INPUT)


def test_gateway_non_json_success_is_unavailable() -> None:
    """A 200 answer that is not JSON is unavailable."""
    gateway = _gateway(lambda _request: httpx.Response(200, content=b"<html>"))

    with pytest.raises(MetricHistoryUnavailableError):
        gateway.read(INPUT)


def test_gateway_connection_error_is_unavailable() -> None:
    """A transport failure is unavailable and names its cause."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(MetricHistoryUnavailableError, match="connection refused"):
        _gateway(handler).read(INPUT)


def test_gateway_malformed_sample_is_unavailable() -> None:
    """Malformed sample entries are unavailable, not an exception of another type."""
    body = _matrix({"metric": {"__name__": "iceberg_table_snapshots"}, "values": [["x"]]})

    with pytest.raises(MetricHistoryUnavailableError):
        _gateway(_answer(body)).read(INPUT)
