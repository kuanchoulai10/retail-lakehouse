"""Define the UpdateTableMaintenancePresetService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table_maintenance_preset import (
    UpdateTableMaintenancePresetUseCase,
    UpdateTableMaintenancePresetUseCaseInput,
    UpdateTableMaintenancePresetUseCaseOutput,
)
from application.service.shared import maintenance_settings_from_dict
from application.service.table_maintenance_preset.table_maintenance_preset_output_fields import (
    table_maintenance_preset_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class UpdateTableMaintenancePresetService(UpdateTableMaintenancePresetUseCase):
    """Rename a table maintenance preset and/or replace its settings."""

    def __init__(
        self,
        presets_repo: TableMaintenancePresetsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._presets_repo = presets_repo
        self._clock = clock

    def execute(
        self, request: UpdateTableMaintenancePresetUseCaseInput
    ) -> UpdateTableMaintenancePresetUseCaseOutput:
        """Apply the given changes; omitted fields stay as they are."""
        preset = self._presets_repo.get(TableMaintenancePresetId(request.id))
        if preset is None:
            raise NotFoundError(f"table maintenance preset {request.id} not found")
        now = self._clock()
        settings = (
            None
            if request.settings is None
            else maintenance_settings_from_dict(request.settings)
        )
        if request.name is not None:
            name = request.name.strip()
            if not name:
                raise ValidationError("preset name must not be blank")
            other = self._presets_repo.find_by_name(name)
            if other is not None and other.id != preset.id:
                raise ConflictError(f"preset name {name!r} already exists")
            preset.rename(name, now)
        if settings is not None:
            preset.update_settings(settings, now)
        self._presets_repo.update(preset)
        return UpdateTableMaintenancePresetUseCaseOutput(
            **table_maintenance_preset_output_fields(preset)
        )
