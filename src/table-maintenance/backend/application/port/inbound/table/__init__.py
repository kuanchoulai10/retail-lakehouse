"""Inbound ports for the table group."""

from __future__ import annotations

from application.port.inbound.table.exclude_table.input import ExcludeTableUseCaseInput
from application.port.inbound.table.exclude_table.output import (
    ExcludeTableUseCaseOutput,
)
from application.port.inbound.table.exclude_table.use_case import ExcludeTableUseCase
from application.port.inbound.table.get_table.input import GetTableUseCaseInput
from application.port.inbound.table.get_table.output import GetTableUseCaseOutput
from application.port.inbound.table.get_table.use_case import GetTableUseCase
from application.port.inbound.table.get_table_metadata.input import (
    GetTableMetadataUseCaseInput,
)
from application.port.inbound.table.get_table_metadata.output import (
    GetTableMetadataUseCaseOutput,
)
from application.port.inbound.table.get_table_metadata.use_case import (
    GetTableMetadataUseCase,
)
from application.port.inbound.table.include_table.input import IncludeTableUseCaseInput
from application.port.inbound.table.include_table.output import (
    IncludeTableUseCaseOutput,
)
from application.port.inbound.table.include_table.use_case import IncludeTableUseCase
from application.port.inbound.table.list_tables.input import ListTablesUseCaseInput
from application.port.inbound.table.list_tables.output import (
    ListTablesUseCaseOutput,
    ListTablesUseCaseOutputItem,
)
from application.port.inbound.table.list_tables.use_case import ListTablesUseCase
from application.port.inbound.table.pause_table.input import PauseTableUseCaseInput
from application.port.inbound.table.pause_table.output import PauseTableUseCaseOutput
from application.port.inbound.table.pause_table.use_case import PauseTableUseCase
from application.port.inbound.table.plan_table_maintenance.input import (
    PlanTableMaintenanceUseCaseInput,
)
from application.port.inbound.table.plan_table_maintenance.output import (
    PlanTableMaintenanceUseCaseOutput,
    PlanTableMaintenanceUseCaseOutputFilterItem,
    PlanTableMaintenanceUseCaseOutputItem,
)
from application.port.inbound.table.plan_table_maintenance.use_case import (
    PlanTableMaintenanceUseCase,
)
from application.port.inbound.table.process_table_hint.input import (
    ProcessTableHintUseCaseInput,
)
from application.port.inbound.table.process_table_hint.output import (
    ProcessTableHintUseCaseOutput,
)
from application.port.inbound.table.process_table_hint.use_case import (
    ProcessTableHintUseCase,
)
from application.port.inbound.table.reset_table_selection.input import (
    ResetTableSelectionUseCaseInput,
)
from application.port.inbound.table.reset_table_selection.output import (
    ResetTableSelectionUseCaseOutput,
)
from application.port.inbound.table.reset_table_selection.use_case import (
    ResetTableSelectionUseCase,
)
from application.port.inbound.table.resume_table.input import ResumeTableUseCaseInput
from application.port.inbound.table.resume_table.output import ResumeTableUseCaseOutput
from application.port.inbound.table.resume_table.use_case import ResumeTableUseCase
from application.port.inbound.table.sync_discovered_tables.input import (
    SyncDiscoveredTablesUseCaseInput,
)
from application.port.inbound.table.sync_discovered_tables.output import (
    SyncDiscoveredTablesUseCaseOutput,
)
from application.port.inbound.table.sync_discovered_tables.use_case import (
    SyncDiscoveredTablesUseCase,
)
from application.port.inbound.table.trigger_table_maintenance.input import (
    TriggerTableMaintenanceUseCaseInput,
)
from application.port.inbound.table.trigger_table_maintenance.output import (
    TriggerTableMaintenanceUseCaseOutput,
)
from application.port.inbound.table.trigger_table_maintenance.use_case import (
    TriggerTableMaintenanceUseCase,
)
from application.port.inbound.table.update_table_settings.input import (
    UpdateTableSettingsUseCaseInput,
)
from application.port.inbound.table.update_table_settings.output import (
    UpdateTableSettingsUseCaseOutput,
)
from application.port.inbound.table.update_table_settings.use_case import (
    UpdateTableSettingsUseCase,
)

__all__ = [
    "ExcludeTableUseCase",
    "ExcludeTableUseCaseInput",
    "ExcludeTableUseCaseOutput",
    "GetTableUseCase",
    "GetTableUseCaseInput",
    "GetTableUseCaseOutput",
    "GetTableMetadataUseCase",
    "GetTableMetadataUseCaseInput",
    "GetTableMetadataUseCaseOutput",
    "IncludeTableUseCase",
    "IncludeTableUseCaseInput",
    "IncludeTableUseCaseOutput",
    "ListTablesUseCase",
    "ListTablesUseCaseInput",
    "ListTablesUseCaseOutput",
    "ListTablesUseCaseOutputItem",
    "PauseTableUseCase",
    "PauseTableUseCaseInput",
    "PauseTableUseCaseOutput",
    "PlanTableMaintenanceUseCase",
    "PlanTableMaintenanceUseCaseInput",
    "PlanTableMaintenanceUseCaseOutput",
    "PlanTableMaintenanceUseCaseOutputFilterItem",
    "PlanTableMaintenanceUseCaseOutputItem",
    "ProcessTableHintUseCase",
    "ProcessTableHintUseCaseInput",
    "ProcessTableHintUseCaseOutput",
    "ResetTableSelectionUseCase",
    "ResetTableSelectionUseCaseInput",
    "ResetTableSelectionUseCaseOutput",
    "ResumeTableUseCase",
    "ResumeTableUseCaseInput",
    "ResumeTableUseCaseOutput",
    "SyncDiscoveredTablesUseCase",
    "SyncDiscoveredTablesUseCaseInput",
    "SyncDiscoveredTablesUseCaseOutput",
    "TriggerTableMaintenanceUseCase",
    "TriggerTableMaintenanceUseCaseInput",
    "TriggerTableMaintenanceUseCaseOutput",
    "UpdateTableSettingsUseCase",
    "UpdateTableSettingsUseCaseInput",
    "UpdateTableSettingsUseCaseOutput",
]
