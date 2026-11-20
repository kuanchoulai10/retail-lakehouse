"""Define the ReadTableMetricHistoryPrometheusGateway."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import httpx

from context.table_maintenance.adapter.outbound.table.prometheus.promql_string import promql_string
from context.table_maintenance.application.port.outbound.table import (
    MetricHistoryUnavailableError,
    ReadTableMetricHistoryGateway,
    ReadTableMetricHistoryGatewayOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetricHistoryGatewayInput

_FIELD_BY_SERIES: dict[tuple[str, str | None], str] = {
    ("iceberg_table_files", "data"): "data_files",
    ("iceberg_table_files", "position_delete"): "position_delete_files",
    ("iceberg_table_files", "equality_delete"): "equality_delete_files",
    ("iceberg_table_files", "deletion_vector"): "deletion_vectors",
    ("iceberg_table_data_size_bytes", None): "data_size_bytes",
    ("iceberg_table_data_records", None): "data_records",
    ("iceberg_table_position_delete_records", None): "position_delete_records",
    ("iceberg_table_equality_delete_records", None): "equality_delete_records",
    ("iceberg_table_reducible_files", None): "reducible_files",
    ("iceberg_table_manifests", None): "manifests",
    ("iceberg_table_manifests_size_bytes", None): "manifests_size_bytes",
    ("iceberg_table_manifest_entries", "added"): "manifest_added_entries",
    ("iceberg_table_manifest_entries", "existing"): "manifest_existing_entries",
    ("iceberg_table_manifest_entries", "deleted"): "manifest_deleted_entries",
    ("iceberg_table_snapshots", None): "snapshots",
}
_LABEL_BY_NAME: dict[str, str] = {
    "iceberg_table_files": "content",
    "iceberg_table_manifest_entries": "status",
}


def _field_of(labels: dict[str, str]) -> str | None:
    name = labels.get("__name__", "")
    label = _LABEL_BY_NAME.get(name)
    return _FIELD_BY_SERIES.get((name, labels.get(label) if label else None))


def _number(raw: object) -> float | None:
    value = float(str(raw))
    return value if math.isfinite(value) else None


class ReadTableMetricHistoryPrometheusGateway(ReadTableMetricHistoryGateway):
    """Read a table's metric series with one ``query_range`` call on a fixed selector.

    The selector is every ``iceberg_table_`` series of the table's uuid; the series name and its
    ``content`` or ``status`` label say which metric count field a series is. ``info`` and the
    observation time are not fields and are ignored. Prometheus's ``NaN`` and infinities are None.
    """

    def __init__(self, base_url: str, client: httpx.Client) -> None:
        """Keep the Prometheus base url and the injected HTTP client."""
        self._base_url = base_url.rstrip("/")
        self._client = client

    def read(
        self,
        input: ReadTableMetricHistoryGatewayInput,  # noqa: A002
    ) -> ReadTableMetricHistoryGatewayOutput:
        """Return the series of every field Prometheus has data for, aligned with the window's grid.

        Two series mapping to one field (for example two scraped instances) give the larger value at a
        point. A transport error, an HTTP error, an error status or an answer that is not a matrix
        raises MetricHistoryUnavailableError.
        """
        result = self._query_range(input)
        count = round((input.end_seconds - input.start_seconds) / input.step_seconds) + 1
        timestamps = [input.start_seconds + index * input.step_seconds for index in range(count)]
        series: dict[str, list[float | None]] = {}
        try:
            for item in result:
                field = _field_of(item["metric"])
                if field is None:
                    continue
                values = series.setdefault(field, [None] * count)
                for timestamp, raw in item["values"]:
                    position = (float(timestamp) - input.start_seconds) / input.step_seconds
                    index = round(position)
                    if abs(position - index) > 1e-6 or not 0 <= index < count:
                        continue
                    value = _number(raw)
                    if value is not None and (values[index] is None or value > values[index]):
                        values[index] = value
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise MetricHistoryUnavailableError(
                f"Prometheus answered a series this gateway cannot read: {exc!r}"
            ) from exc
        return ReadTableMetricHistoryGatewayOutput(timestamps=timestamps, series=series)

    def _query_range(self, input: ReadTableMetricHistoryGatewayInput) -> list[dict[str, Any]]:  # noqa: A002
        params = {
            "query": f'{{__name__=~"iceberg_table_.+", table_uuid={promql_string(input.table_uuid)}}}',
            "start": str(input.start_seconds),
            "end": str(input.end_seconds),
            "step": str(input.step_seconds),
        }
        try:
            response = self._client.get(f"{self._base_url}/api/v1/query_range", params=params)
        except httpx.HTTPError as exc:
            raise MetricHistoryUnavailableError(f"Prometheus is unreachable: {exc}") from exc
        body = self._json(response)
        error = body.get("error") if isinstance(body, dict) else None
        if not response.is_success:
            detail = f": {error}" if error else ""
            raise MetricHistoryUnavailableError(f"Prometheus answered HTTP {response.status_code}{detail}")
        if not isinstance(body, dict) or body.get("status") != "success":
            raise MetricHistoryUnavailableError(f"Prometheus reported an error: {error or 'no success status'}")
        data = body.get("data")
        if not isinstance(data, dict) or data.get("resultType") != "matrix" or not isinstance(data.get("result"), list):
            raise MetricHistoryUnavailableError("Prometheus answered something other than a matrix")
        return data["result"]

    @staticmethod
    def _json(response: httpx.Response) -> Any:  # noqa: ANN401
        try:
            return response.json()
        except ValueError:
            return None
