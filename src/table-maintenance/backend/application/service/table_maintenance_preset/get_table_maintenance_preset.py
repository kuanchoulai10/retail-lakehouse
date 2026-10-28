"""Define the GetTableMaintenancePresetService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import NotFoundError
from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset import (
    GetTableMaintenancePresetUseCase,
    GetTableMaintenancePresetUseCaseInput,
    GetTableMaintenancePresetUseCaseOutput,
)
from application.service.table_maintenance_preset.table_maintenance_preset_output_fields import (
    table_maintenance_preset_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )


class GetTableMaintenancePresetService(GetTableMaintenancePresetUseCase):
    """Get one table maintenance preset."""

    def __init__(self, presets_repo: TableMaintenancePresetsRepo) -> None:
        """Bind the repo."""
        self._presets_repo = presets_repo

    def execute(
        self, request: GetTableMaintenancePresetUseCaseInput
    ) -> GetTableMaintenancePresetUseCaseOutput:
        """Return the preset or raise NotFoundError."""
        preset = self._presets_repo.get(TableMaintenancePresetId(request.id))
        if preset is None:
            raise NotFoundError(f"table maintenance preset {request.id} not found")
        return GetTableMaintenancePresetUseCaseOutput(
            **table_maintenance_preset_output_fields(preset)
        )
