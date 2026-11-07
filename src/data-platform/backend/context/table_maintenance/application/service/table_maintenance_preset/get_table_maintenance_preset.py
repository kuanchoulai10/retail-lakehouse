"""Define the GetTableMaintenancePresetService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    GetTableMaintenancePresetUseCase,
    GetTableMaintenancePresetUseCaseInput,
    GetTableMaintenancePresetUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_preset.table_maintenance_preset_output_fields import (  # noqa: E501
    table_maintenance_preset_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class GetTableMaintenancePresetService(GetTableMaintenancePresetUseCase):
    """Get one table maintenance preset."""

    def __init__(self, presets_repo: TableMaintenancePresetsRepo) -> None:
        """Bind the repo."""
        self._presets_repo = presets_repo

    def execute(self, request: GetTableMaintenancePresetUseCaseInput) -> GetTableMaintenancePresetUseCaseOutput:
        """Return the preset or raise NotFoundError."""
        preset = self._presets_repo.get(TableMaintenancePresetId(request.id))
        if preset is None:
            raise NotFoundError(f"table maintenance preset {request.id} not found")
        return GetTableMaintenancePresetUseCaseOutput(**table_maintenance_preset_output_fields(preset))
