"""Define the maintenance run router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.table_maintenance_run.dto import (
    TableMaintenanceRunApiResponse,
    ProcessTableMaintenanceCallbackApiRequest,
    ProcessTableMaintenanceCallbackApiResponse,
)
from adapter.inbound.web import web_use_cases, WebUseCases
from application.port.inbound.table_maintenance_run import (
    GetTableMaintenanceRunUseCaseInput,
    ListTableMaintenanceRunsUseCaseInput,
    ProcessTableMaintenanceCallbackUseCaseInput,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(tags=["table-maintenance-runs"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("/tables/{table_uuid}/table-maintenance-runs")
def list_table_maintenance_runs(
    table_uuid: str,
    use_cases: UseCases,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[TableMaintenanceRunApiResponse]:
    """List the latest maintenance runs of a table."""
    output = use_cases.list_table_maintenance_runs.execute(
        ListTableMaintenanceRunsUseCaseInput(table_uuid=table_uuid, limit=limit)
    )
    return [
        TableMaintenanceRunApiResponse.model_validate(item) for item in output.items
    ]


@router.get("/table-maintenance-runs/{run_id}")
def get_table_maintenance_run(
    run_id: str, use_cases: UseCases
) -> TableMaintenanceRunApiResponse:
    """Return one maintenance run."""
    output = use_cases.get_table_maintenance_run.execute(
        GetTableMaintenanceRunUseCaseInput(run_id=run_id)
    )
    return TableMaintenanceRunApiResponse.model_validate(output)


@router.post(
    "/table-maintenance-runs/{run_id}/operations/{operation}/result",
    status_code=status.HTTP_202_ACCEPTED,
)
def process_table_maintenance_callback(
    run_id: str,
    operation: str,
    body: ProcessTableMaintenanceCallbackApiRequest,
    use_cases: UseCases,
) -> ProcessTableMaintenanceCallbackApiResponse:
    """Accept the result a Spark job reports for one operation attempt."""
    if body.run_id is not None and body.run_id != run_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "body run_id differs from the path"
        )
    if body.operation is not None and body.operation != operation:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "body operation differs from the path",
        )
    output = use_cases.process_table_maintenance_callback.execute(
        ProcessTableMaintenanceCallbackUseCaseInput(
            run_id=run_id,
            operation=operation,
            attempt=body.attempt,
            succeeded=body.succeeded,
            metrics=body.metrics,
            error=body.error,
        )
    )
    return ProcessTableMaintenanceCallbackApiResponse.model_validate(output)
