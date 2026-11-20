"""Define the table metrics router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table.table_metrics_exposition import (
    render_table_metrics_exposition,
)
from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseInput

table_metrics_router = APIRouter(tags=["table-metrics"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_EXPOSITION_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"


@table_metrics_router.get("/table-metrics", include_in_schema=False)
def get_table_metrics(use_cases: UseCases) -> PlainTextResponse:
    """Export every managed table's saved metrics in the Prometheus text format; Prometheus is the only caller."""
    output = use_cases.list_table_metrics.execute(ListTableMetricsUseCaseInput())
    return PlainTextResponse(render_table_metrics_exposition(output), media_type=_EXPOSITION_MEDIA_TYPE)
