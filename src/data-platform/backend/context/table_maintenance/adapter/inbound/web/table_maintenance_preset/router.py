"""Define the table maintenance preset router."""

from __future__ import annotations

from typing import Annotated

from context.table_maintenance.adapter.inbound.web.table_maintenance_preset.dto import (
    CreateTableMaintenancePresetApiRequest,
    TableMaintenancePresetApiResponse,
    UpdateTableMaintenancePresetApiRequest,
)
from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
    DeleteTableMaintenancePresetUseCaseInput,
    GetTableMaintenancePresetUseCaseInput,
    ListTableMaintenancePresetsUseCaseInput,
    UpdateTableMaintenancePresetUseCaseInput,
)
from fastapi import APIRouter, Depends, Response, status

router = APIRouter(prefix="/table-maintenance-presets", tags=["table-maintenance-presets"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def list_table_maintenance_presets(
    use_cases: UseCases,
) -> list[TableMaintenancePresetApiResponse]:
    """List the table maintenance presets."""
    output = use_cases.list_table_maintenance_presets.execute(ListTableMaintenancePresetsUseCaseInput())
    return [TableMaintenancePresetApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table_maintenance_preset(
    body: CreateTableMaintenancePresetApiRequest, use_cases: UseCases
) -> TableMaintenancePresetApiResponse:
    """Create a table maintenance preset."""
    output = use_cases.create_table_maintenance_preset.execute(
        CreateTableMaintenancePresetUseCaseInput(name=body.name, settings=body.settings)
    )
    return TableMaintenancePresetApiResponse.model_validate(output)


@router.get("/{preset_id}")
def get_table_maintenance_preset(preset_id: str, use_cases: UseCases) -> TableMaintenancePresetApiResponse:
    """Return one table maintenance preset."""
    output = use_cases.get_table_maintenance_preset.execute(GetTableMaintenancePresetUseCaseInput(id=preset_id))
    return TableMaintenancePresetApiResponse.model_validate(output)


@router.patch("/{preset_id}")
def update_table_maintenance_preset(
    preset_id: str, body: UpdateTableMaintenancePresetApiRequest, use_cases: UseCases
) -> TableMaintenancePresetApiResponse:
    """Change the name or the settings of a table maintenance preset."""
    output = use_cases.update_table_maintenance_preset.execute(
        UpdateTableMaintenancePresetUseCaseInput(id=preset_id, name=body.name, settings=body.settings)
    )
    return TableMaintenancePresetApiResponse.model_validate(output)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table_maintenance_preset(preset_id: str, use_cases: UseCases) -> Response:
    """Delete a table maintenance preset."""
    use_cases.delete_table_maintenance_preset.execute(DeleteTableMaintenancePresetUseCaseInput(id=preset_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
