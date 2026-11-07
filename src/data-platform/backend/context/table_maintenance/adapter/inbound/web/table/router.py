"""Define the table router."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated

from context.table_maintenance.adapter.inbound.web.table.dto import (
    ExcludeTableApiRequest,
    IncludeTableApiRequest,
    TableApiResponse,
    TableCommitsApiResponse,
    TableHealthApiResponse,
    TableMetadataApiResponse,
    TableStorageApiResponse,
    TriggerTableMaintenanceApiRequest,
    TriggerTableMaintenanceApiResponse,
    UpdateTableSettingsApiRequest,
)
from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.application.port.inbound.table import (
    ExcludeTableUseCaseInput,
    GetTableHealthUseCaseInput,
    GetTableMetadataUseCaseInput,
    GetTableStorageUseCaseInput,
    GetTableUseCaseInput,
    IncludeTableUseCaseInput,
    ListTableCommitsUseCaseInput,
    ListTablesUseCaseInput,
    PauseTableUseCaseInput,
    ResetTableSelectionUseCaseInput,
    ResumeTableUseCaseInput,
    TriggerTableMaintenanceUseCaseInput,
    UpdateTableSettingsUseCaseInput,
)
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def list_tables(use_cases: UseCases, status: str | None = None) -> list[TableApiResponse]:
    """List the tables, optionally only those in one status."""
    output = use_cases.list_tables.execute(ListTablesUseCaseInput(status=status))
    return [TableApiResponse.model_validate(item) for item in output.items]


@router.post("/include")
def include_table(body: IncludeTableApiRequest, use_cases: UseCases) -> TableApiResponse:
    """Include a catalog table in maintenance by hand."""
    output = use_cases.include_table.execute(IncludeTableUseCaseInput(**body.model_dump()))
    return TableApiResponse.model_validate(output)


@router.post("/exclude")
def exclude_table(body: ExcludeTableApiRequest, use_cases: UseCases) -> TableApiResponse:
    """Exclude a catalog table from maintenance by hand."""
    output = use_cases.exclude_table.execute(ExcludeTableUseCaseInput(**body.model_dump()))
    return TableApiResponse.model_validate(output)


@router.get("/{table_uuid}")
def get_table(table_uuid: str, use_cases: UseCases) -> TableApiResponse:
    """Return one table."""
    output = use_cases.get_table.execute(GetTableUseCaseInput(uuid=table_uuid))
    return TableApiResponse.model_validate(output)


@router.get("/{table_uuid}/metadata")
def get_table_metadata(table_uuid: str, use_cases: UseCases) -> TableMetadataApiResponse:
    """Return the catalog metadata of one table."""
    output = use_cases.get_table_metadata.execute(GetTableMetadataUseCaseInput(uuid=table_uuid))
    return TableMetadataApiResponse.model_validate(output)


@router.get("/{table_uuid}/health")
def get_table_health(table_uuid: str, use_cases: UseCases) -> TableHealthApiResponse:
    """Return the scheduler's maintenance evaluation of one table."""
    output = use_cases.get_table_health.execute(GetTableHealthUseCaseInput(uuid=table_uuid))
    return TableHealthApiResponse.model_validate(output)


@router.get("/{table_uuid}/storage")
def get_table_storage(table_uuid: str, use_cases: UseCases) -> TableStorageApiResponse:
    """Return the current and old-snapshot storage of one table."""
    output = use_cases.get_table_storage.execute(GetTableStorageUseCaseInput(uuid=table_uuid))
    return TableStorageApiResponse.model_validate(output)


@router.get("/{table_uuid}/commits")
def list_table_commits(
    table_uuid: str,
    use_cases: UseCases,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    since: datetime | None = None,
) -> TableCommitsApiResponse:
    """Return the commits of one table, newest first."""
    output = use_cases.list_table_commits.execute(
        ListTableCommitsUseCaseInput(uuid=table_uuid, limit=limit, since=since)
    )
    return TableCommitsApiResponse.model_validate(output)


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
    output = use_cases.reset_table_selection.execute(ResetTableSelectionUseCaseInput(uuid=table_uuid))
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
