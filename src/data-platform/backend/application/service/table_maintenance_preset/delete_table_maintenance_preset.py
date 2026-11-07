"""Define the DeleteTableMaintenancePresetService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.table_maintenance_preset import (
    DeleteTableMaintenancePresetUseCase,
    DeleteTableMaintenancePresetUseCaseInput,
    DeleteTableMaintenancePresetUseCaseOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_rule import TableDiscoveryRulesRepo
    from application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class DeleteTableMaintenancePresetService(DeleteTableMaintenancePresetUseCase):
    """Delete a table maintenance preset that no discovery rule references."""

    def __init__(
        self,
        presets_repo: TableMaintenancePresetsRepo,
        rules_repo: TableDiscoveryRulesRepo,
    ) -> None:
        """Bind the preset and rule repos."""
        self._presets_repo = presets_repo
        self._rules_repo = rules_repo

    def execute(
        self, request: DeleteTableMaintenancePresetUseCaseInput
    ) -> DeleteTableMaintenancePresetUseCaseOutput:
        """Delete the preset unless a rule still uses it."""
        preset_id = TableMaintenancePresetId(request.id)
        if self._presets_repo.get(preset_id) is None:
            raise NotFoundError(f"table maintenance preset {request.id} not found")
        if self._rules_repo.count_by_preset(preset_id) > 0:
            raise ConflictError(
                f"table maintenance preset {request.id} is referenced by discovery rules"
            )
        self._presets_repo.delete(preset_id)
        return DeleteTableMaintenancePresetUseCaseOutput()
