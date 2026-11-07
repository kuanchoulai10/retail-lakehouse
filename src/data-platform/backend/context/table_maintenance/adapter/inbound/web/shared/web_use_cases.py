"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_discovery_settings import (
        GetTableDiscoverySettingsUseCase,
        UpdateTableDiscoverySettingsUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        SyncDiscoveredTablesUseCase,
        ExcludeTableUseCase,
        GetTableHealthUseCase,
        GetTableMetadataUseCase,
        GetTableStorageUseCase,
        GetTableUseCase,
        IncludeTableUseCase,
        ListTableCommitsUseCase,
        ListTablesUseCase,
        PauseTableUseCase,
        ResetTableSelectionUseCase,
        ResumeTableUseCase,
        TriggerTableMaintenanceUseCase,
        UpdateTableSettingsUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_rule import (
        CreateTableDiscoveryRuleUseCase,
        DeleteTableDiscoveryRuleUseCase,
        ListTableDiscoveryRulesUseCase,
        UpdateTableDiscoveryRuleUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
        CreateTableMaintenancePresetUseCase,
        DeleteTableMaintenancePresetUseCase,
        GetTableMaintenancePresetUseCase,
        ListTableMaintenancePresetsUseCase,
        UpdateTableMaintenancePresetUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every use case the web API calls; the composition root builds it."""

    create_table_discovery_rule: CreateTableDiscoveryRuleUseCase
    list_table_discovery_rules: ListTableDiscoveryRulesUseCase
    update_table_discovery_rule: UpdateTableDiscoveryRuleUseCase
    delete_table_discovery_rule: DeleteTableDiscoveryRuleUseCase
    get_table_discovery_settings: GetTableDiscoverySettingsUseCase
    update_table_discovery_settings: UpdateTableDiscoverySettingsUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    create_table_maintenance_preset: CreateTableMaintenancePresetUseCase
    list_table_maintenance_presets: ListTableMaintenancePresetsUseCase
    get_table_maintenance_preset: GetTableMaintenancePresetUseCase
    update_table_maintenance_preset: UpdateTableMaintenancePresetUseCase
    delete_table_maintenance_preset: DeleteTableMaintenancePresetUseCase
    list_tables: ListTablesUseCase
    get_table: GetTableUseCase
    get_table_health: GetTableHealthUseCase
    get_table_metadata: GetTableMetadataUseCase
    get_table_storage: GetTableStorageUseCase
    list_table_commits: ListTableCommitsUseCase
    update_table_settings: UpdateTableSettingsUseCase
    pause_table: PauseTableUseCase
    resume_table: ResumeTableUseCase
    reset_table_selection: ResetTableSelectionUseCase
    include_table: IncludeTableUseCase
    exclude_table: ExcludeTableUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
