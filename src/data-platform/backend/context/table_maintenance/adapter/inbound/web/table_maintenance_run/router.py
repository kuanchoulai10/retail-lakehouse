"""Define the maintenance run router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run.dto import (
    ForwardTableMaintenanceResultApiRequest,
    ForwardTableMaintenanceResultApiResponse,
    TableMaintenanceRunApiResponse,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    ForwardTableMaintenanceResultUseCaseInput,
    GetTableMaintenanceRunUseCaseInput,
    ListTableMaintenanceRunsUseCaseInput,
)

router = APIRouter(tags=["table-maintenance-runs"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]
RunId = Annotated[
    str,
    Path(description="An `mr-` id (prefix, dash, 26 lowercase Crockford base32 characters; ADR 0011)."),
]


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
    return [TableMaintenanceRunApiResponse.model_validate(item) for item in output.items]


@router.get("/table-maintenance-runs/{run_id}")
def get_table_maintenance_run(run_id: RunId, use_cases: UseCases) -> TableMaintenanceRunApiResponse:
    """Return one maintenance run."""
    output = use_cases.get_table_maintenance_run.execute(GetTableMaintenanceRunUseCaseInput(run_id=run_id))
    return TableMaintenanceRunApiResponse.model_validate(output)


@router.post(
    "/table-maintenance-runs/{run_id}/result",
    status_code=status.HTTP_202_ACCEPTED,
)
def forward_table_maintenance_result(
    run_id: RunId,
    body: ForwardTableMaintenanceResultApiRequest,
    use_cases: UseCases,
) -> ForwardTableMaintenanceResultApiResponse:
    """Accept the result a Spark job reports for one attempt of the run.

    The run names its operation. A body that names another one is refused with 422.
    """
    if body.run_id is not None and body.run_id != run_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "body run_id differs from the path")
    output = use_cases.forward_table_maintenance_result.execute(
        ForwardTableMaintenanceResultUseCaseInput(
            run_id=run_id,
            operation=body.operation,
            attempt=body.attempt,
            succeeded=body.succeeded,
            metrics=body.metrics,
            error=body.error,
        )
    )
    return ForwardTableMaintenanceResultApiResponse.model_validate(output)
