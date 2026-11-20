"""Test that the exposition's metric names and the Prometheus gateway's query mapping agree.

The two adapters cannot share code, so this test is the one place that holds both to the same names.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from context.table_maintenance.adapter.inbound.web.table import render_table_metrics_exposition
from context.table_maintenance.adapter.outbound.table.prometheus import ReadTableMetricHistoryPrometheusGateway
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS
from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseOutput
from context.table_maintenance.application.port.outbound.table import ReadTableMetricHistoryGatewayInput

START = 1_000_000.0
SAMPLE = re.compile(r"^(?P<name>[a-z_]+)\{(?P<labels>[^}]*)\} (?P<value>\S+)$")
LABEL = re.compile(r'(\w+)="([^"]*)"')


def _exposition_as_prometheus_answer(text: str) -> dict[str, Any]:
    """Turn each sample line of the exposition into one series with a single value at ``START``."""
    result = []
    for line in text.splitlines():
        match = SAMPLE.match(line)
        if match is None:
            continue
        labels = dict(LABEL.findall(match["labels"]))
        result.append(
            {
                "metric": {"__name__": match["name"], "job": "table-maintenance-api", **labels},
                "values": [[START, match["value"]]],
            }
        )
    return {"status": "success", "data": {"resultType": "matrix", "result": result}}


def test_every_count_field_round_trips_through_the_exposition_and_the_gateway() -> None:
    """Each of the 15 counts, rendered under its exposition name, is read back under the same field."""
    counts = {field: index * 10 + 7 for index, field in enumerate(TABLE_METRIC_COUNT_FIELDS, start=1)}
    exposition = render_table_metrics_exposition(
        ListTableMetricsUseCaseOutput(
            tables=(
                ListTableMetricsUseCaseOutput.Table(
                    table_uuid="u1",
                    catalog="iceberg",
                    namespace="retail",
                    table="orders",
                    observed_at=datetime(2026, 11, 20, 12, tzinfo=UTC),
                    counts=counts,
                ),
            )
        )
    )
    answer = _exposition_as_prometheus_answer(exposition)
    gateway = ReadTableMetricHistoryPrometheusGateway(
        "http://prometheus:9090",
        httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=answer))),
    )

    output = gateway.read(
        ReadTableMetricHistoryGatewayInput(table_uuid="u1", start_seconds=START, end_seconds=START, step_seconds=30)
    )

    assert set(output.series) == set(TABLE_METRIC_COUNT_FIELDS)
    assert {field: values[0] for field, values in output.series.items()} == {
        field: float(value) for field, value in counts.items()
    }
