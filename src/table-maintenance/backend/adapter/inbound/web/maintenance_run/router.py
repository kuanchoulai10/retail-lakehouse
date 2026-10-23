"""Define the maintenance run router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.maintenance_run.dto import (
    MaintenanceRunApiResponse,
    ProcessMaintenanceCallbackApiRequest,
    ProcessMaintenanceCallbackApiResponse,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.maintenance_run.get_maintenance_run import (
    GetMaintenanceRunUseCaseInput,
)
from application.port.inbound.maintenance_run.list_maintenance_runs import (
    ListMaintenanceRunsUseCaseInput,
)
from application.port.inbound.maintenance_run.process_maintenance_callback import (
    ProcessMaintenanceCallbackUseCaseInput,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(tags=["maintenance-runs"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("/tables/{table_uuid}/runs")
def list_maintenance_runs(
    table_uuid: str,
    use_cases: UseCases,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[MaintenanceRunApiResponse]:
    """List the latest maintenance runs of a table."""
    output = use_cases.list_maintenance_runs.execute(
        ListMaintenanceRunsUseCaseInput(table_uuid=table_uuid, limit=limit)
    )
    return [MaintenanceRunApiResponse.model_validate(item) for item in output.items]


@router.get("/runs/{run_id}")
def get_maintenance_run(run_id: str, use_cases: UseCases) -> MaintenanceRunApiResponse:
    """Return one maintenance run."""
    output = use_cases.get_maintenance_run.execute(
        GetMaintenanceRunUseCaseInput(run_id=run_id)
    )
    return MaintenanceRunApiResponse.model_validate(output)


@router.post(
    "/runs/{run_id}/operations/{operation}/result",
    status_code=status.HTTP_202_ACCEPTED,
)
def process_maintenance_callback(
    run_id: str,
    operation: str,
    body: ProcessMaintenanceCallbackApiRequest,
    use_cases: UseCases,
) -> ProcessMaintenanceCallbackApiResponse:
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
    output = use_cases.process_maintenance_callback.execute(
        ProcessMaintenanceCallbackUseCaseInput(
            run_id=run_id,
            operation=operation,
            attempt=body.attempt,
            succeeded=body.succeeded,
            metrics=body.metrics,
            error=body.error,
        )
    )
    return ProcessMaintenanceCallbackApiResponse.model_validate(output)
