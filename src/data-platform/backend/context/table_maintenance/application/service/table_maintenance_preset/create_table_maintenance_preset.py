"""Define the CreateTableMaintenancePresetService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    CreateTableMaintenancePresetUseCase,
    CreateTableMaintenancePresetUseCaseInput,
    CreateTableMaintenancePresetUseCaseOutput,
)
from context.table_maintenance.application.service.shared import (
    maintenance_settings_from_dict,
)
from context.table_maintenance.application.service.table_maintenance_preset.table_maintenance_preset_output_fields import (
    table_maintenance_preset_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class CreateTableMaintenancePresetService(CreateTableMaintenancePresetUseCase):
    """Create a table maintenance preset with a unique name."""

    def __init__(
        self,
        presets_repo: TableMaintenancePresetsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repo, the clock and the id generator."""
        self._presets_repo = presets_repo
        self._clock = clock
        self._new_id = new_id

    def execute(
        self, request: CreateTableMaintenancePresetUseCaseInput
    ) -> CreateTableMaintenancePresetUseCaseOutput:
        """Create the preset, rejecting a blank or taken name."""
        name = request.name.strip()
        if not name:
            raise ValidationError("preset name must not be blank")
        settings = maintenance_settings_from_dict(request.settings)
        if self._presets_repo.find_by_name(name) is not None:
            raise ConflictError(f"preset name {name!r} already exists")
        preset = TableMaintenancePreset.create(
            TableMaintenancePresetId(self._new_id()), name, settings, self._clock()
        )
        self._presets_repo.create(preset)
        return CreateTableMaintenancePresetUseCaseOutput(
            **table_maintenance_preset_output_fields(preset)
        )
