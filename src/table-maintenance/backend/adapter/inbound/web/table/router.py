"""Define the table router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.table.dto import (
    ExcludeTableApiRequest,
    IncludeTableApiRequest,
    TableApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    UpdateTableSettingsApiRequest,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.table.exclude_table import (
    ExcludeTableUseCaseInput,
)
from application.port.inbound.table.get_table import (
    GetTableUseCaseInput,
)
from application.port.inbound.table.include_table import (
    IncludeTableUseCaseInput,
)
from application.port.inbound.table.list_tables import (
    ListTablesUseCaseInput,
)
from application.port.inbound.table.pause_table import (
    PauseTableUseCaseInput,
)
from application.port.inbound.table.reset_table_selection import (
    ResetTableSelectionUseCaseInput,
)
from application.port.inbound.table.resume_table import (
    ResumeTableUseCaseInput,
)
from application.port.inbound.table.trigger_table_maintenance import (
    TriggerTableMaintenanceUseCaseInput,
)
from application.port.inbound.table.update_table_settings import (
    UpdateTableSettingsUseCaseInput,
)
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def list_tables(
    use_cases: UseCases, status: str | None = None
) -> list[TableApiResponse]:
    """List the tables, optionally only those in one status."""
    output = use_cases.list_tables.execute(ListTablesUseCaseInput(status=status))
    return [TableApiResponse.model_validate(item) for item in output.items]


@router.post("/include")
def include_table(
    body: IncludeTableApiRequest, use_cases: UseCases
) -> TableApiResponse:
    """Include a catalog table in maintenance by hand."""
    output = use_cases.include_table.execute(
        IncludeTableUseCaseInput(**body.model_dump())
    )
    return TableApiResponse.model_validate(output)


@router.post("/exclude")
def exclude_table(
    body: ExcludeTableApiRequest, use_cases: UseCases
) -> TableApiResponse:
    """Exclude a catalog table from maintenance by hand."""
    output = use_cases.exclude_table.execute(
        ExcludeTableUseCaseInput(**body.model_dump())
    )
    return TableApiResponse.model_validate(output)


@router.get("/{table_uuid}")
def get_table(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Return one table."""
    output = use_cases.get_table.execute(GetTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.put("/{table_uuid}/settings")
def update_table_settings(
    table_uuid: str, body: UpdateTableSettingsApiRequest, use_cases: UseCases
) -> TableApiResponse:
    """Replace the settings of a table."""
    output = use_cases.update_table_settings.execute(
        UpdateTableSettingsUseCaseInput(uuid=table_uuid, settings=body.root)
    )
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/pause")
def pause_table(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Pause maintenance of a table."""
    output = use_cases.pause_table.execute(PauseTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/resume")
def resume_table(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Resume maintenance of a table."""
    output = use_cases.resume_table.execute(ResumeTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/reset-selection")
def reset_table_selection(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Hand a manually selected table back to the discovery rules."""
    output = use_cases.reset_table_selection.execute(
        ResetTableSelectionUseCaseInput(uuid=table_uuid)
    )
    return TableApiResponse.model_validate(output)


@router.post("/{table_uuid}/maintenance", status_code=status.HTTP_202_ACCEPTED)
def trigger_table_maintenance(
    table_uuid: str, body: TriggerTableMaintenanceApiRequest, use_cases: UseCases
) -> TriggerTableMaintenanceApiResponse:
    """Run the given operations on a table now."""
    output = use_cases.trigger_table_maintenance.execute(
        TriggerTableMaintenanceUseCaseInput(uuid=table_uuid, operations=body.operations)
    )
    return TriggerTableMaintenanceApiResponse.model_validate(output)
