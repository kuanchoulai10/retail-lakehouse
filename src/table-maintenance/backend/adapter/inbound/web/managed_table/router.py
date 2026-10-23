"""Define the managed table router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.managed_table.dto import (
    ExcludeManagedTableApiRequest,
    IncludeManagedTableApiRequest,
    ManagedTableApiResponse,
    TriggerMaintenanceApiRequest,
    TriggerMaintenanceApiResponse,
    UpdateManagedTableSettingsApiRequest,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.managed_table.exclude_managed_table import (
    ExcludeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.get_managed_table import (
    GetManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.include_managed_table import (
    IncludeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.list_managed_tables import (
    ListManagedTablesUseCaseInput,
)
from application.port.inbound.managed_table.pause_managed_table import (
    PauseManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.reset_managed_table_selection import (
    ResetManagedTableSelectionUseCaseInput,
)
from application.port.inbound.managed_table.resume_managed_table import (
    ResumeManagedTableUseCaseInput,
)
from application.port.inbound.managed_table.trigger_maintenance import (
    TriggerMaintenanceUseCaseInput,
)
from application.port.inbound.managed_table.update_managed_table_settings import (
    UpdateManagedTableSettingsUseCaseInput,
)
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def list_managed_tables(
    use_cases: UseCases, status: str | None = None
) -> list[ManagedTableApiResponse]:
    """List the managed tables, optionally only those in one status."""
    output = use_cases.list_managed_tables.execute(
        ListManagedTablesUseCaseInput(status=status)
    )
    return [ManagedTableApiResponse.model_validate(item) for item in output.items]


@router.post("/include")
def include_managed_table(
    body: IncludeManagedTableApiRequest, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Include a catalog table in maintenance by hand."""
    output = use_cases.include_managed_table.execute(
        IncludeManagedTableUseCaseInput(**body.model_dump())
    )
    return ManagedTableApiResponse.model_validate(output)


@router.post("/exclude")
def exclude_managed_table(
    body: ExcludeManagedTableApiRequest, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Exclude a catalog table from maintenance by hand."""
    output = use_cases.exclude_managed_table.execute(
        ExcludeManagedTableUseCaseInput(**body.model_dump())
    )
    return ManagedTableApiResponse.model_validate(output)


@router.get("/{table_uuid}")
def get_managed_table(table_uuid: str, use_cases: UseCases) -> ManagedTableApiResponse:
    """Return one managed table."""
    output = use_cases.get_managed_table.execute(
        GetManagedTableUseCaseInput(uuid=table_uuid)
    )
    return ManagedTableApiResponse.model_validate(output)


@router.put("/{table_uuid}/settings")
def update_managed_table_settings(
    table_uuid: str, body: UpdateManagedTableSettingsApiRequest, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Replace the settings of a managed table."""
    output = use_cases.update_managed_table_settings.execute(
        UpdateManagedTableSettingsUseCaseInput(uuid=table_uuid, settings=body.root)
    )
    return ManagedTableApiResponse.model_validate(output)


@router.post("/{table_uuid}/pause")
def pause_managed_table(
    table_uuid: str, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Pause maintenance of a managed table."""
    output = use_cases.pause_managed_table.execute(
        PauseManagedTableUseCaseInput(uuid=table_uuid)
    )
    return ManagedTableApiResponse.model_validate(output)


@router.post("/{table_uuid}/resume")
def resume_managed_table(
    table_uuid: str, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Resume maintenance of a managed table."""
    output = use_cases.resume_managed_table.execute(
        ResumeManagedTableUseCaseInput(uuid=table_uuid)
    )
    return ManagedTableApiResponse.model_validate(output)


@router.post("/{table_uuid}/reset-selection")
def reset_managed_table_selection(
    table_uuid: str, use_cases: UseCases
) -> ManagedTableApiResponse:
    """Hand a manually selected table back to the discovery rules."""
    output = use_cases.reset_managed_table_selection.execute(
        ResetManagedTableSelectionUseCaseInput(uuid=table_uuid)
    )
    return ManagedTableApiResponse.model_validate(output)


@router.post("/{table_uuid}/maintenance", status_code=status.HTTP_202_ACCEPTED)
def trigger_maintenance(
    table_uuid: str, body: TriggerMaintenanceApiRequest, use_cases: UseCases
) -> TriggerMaintenanceApiResponse:
    """Run the given operations on a table now."""
    output = use_cases.trigger_maintenance.execute(
        TriggerMaintenanceUseCaseInput(uuid=table_uuid, operations=body.operations)
    )
    return TriggerMaintenanceApiResponse.model_validate(output)
