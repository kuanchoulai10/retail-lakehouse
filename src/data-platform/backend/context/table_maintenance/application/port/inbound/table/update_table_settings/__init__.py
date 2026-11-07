"""Replace a table's settings."""

from context.table_maintenance.application.port.inbound.table.update_table_settings.input import (
    UpdateTableSettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.update_table_settings.output import (
    UpdateTableSettingsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table.update_table_settings.use_case import (
    UpdateTableSettingsUseCase,
)

__all__ = [
    "UpdateTableSettingsUseCase",
    "UpdateTableSettingsUseCaseInput",
    "UpdateTableSettingsUseCaseOutput",
]
