"""Provide the seed_default_preset function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
    ListTableMaintenancePresetsUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
        CreateTableMaintenancePresetUseCase,
        ListTableMaintenancePresetsUseCase,
    )

DEFAULT_PRESET_NAME = "default"


def seed_default_preset(
    list_presets: ListTableMaintenancePresetsUseCase,
    create_preset: CreateTableMaintenancePresetUseCase,
) -> bool:
    """Create the ``default`` preset with default settings if none exists.

    Returns whether it created the preset.
    """
    if list_presets.execute(ListTableMaintenancePresetsUseCaseInput()).items:
        return False
    create_preset.execute(
        CreateTableMaintenancePresetUseCaseInput(name=DEFAULT_PRESET_NAME)
    )
    return True
