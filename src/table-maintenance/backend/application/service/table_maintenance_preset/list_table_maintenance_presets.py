"""Define the ListTableMaintenancePresetsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsUseCase,
    ListTableMaintenancePresetsUseCaseInput,
    ListTableMaintenancePresetsUseCaseOutput,
    ListTableMaintenancePresetsUseCaseOutputItem,
)
from application.service.table_maintenance_preset.table_maintenance_preset_output_fields import (
    table_maintenance_preset_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )


class ListTableMaintenancePresetsService(ListTableMaintenancePresetsUseCase):
    """List all table maintenance presets."""

    def __init__(self, presets_repo: TableMaintenancePresetsRepo) -> None:
        """Bind the repo."""
        self._presets_repo = presets_repo

    def execute(
        self,
        request: ListTableMaintenancePresetsUseCaseInput,  # noqa: ARG002
    ) -> ListTableMaintenancePresetsUseCaseOutput:
        """Return every preset."""
        return ListTableMaintenancePresetsUseCaseOutput(
            items=[
                ListTableMaintenancePresetsUseCaseOutputItem(
                    **table_maintenance_preset_output_fields(t)
                )
                for t in self._presets_repo.list_all()
            ]
        )
