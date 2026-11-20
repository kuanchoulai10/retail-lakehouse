"""Define the MetricsSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricsSettings(BaseModel):
    """Where the table metric trends are read from (``GLAC_METRICS__PROMETHEUS_URL``) and how long a query may take.

    ``query_timeout_seconds`` bounds each phase of a request on its own (connect, read, write, pool), not the
    request as one deadline, so one query can take longer than it in all.
    """

    prometheus_url: str = "http://table-metrics-prometheus.table-metrics.svc.cluster.local:9090"
    query_timeout_seconds: float = Field(default=10.0, gt=0)
