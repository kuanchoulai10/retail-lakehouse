"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.inbound.table_discovery_settings.get_table_discovery_settings import (
        GetTableDiscoverySettingsUseCase,
    )
    from application.port.inbound.table.sync_discovered_tables import (
        SyncDiscoveredTablesUseCase,
    )
    from application.port.inbound.table_discovery_settings.update_table_discovery_settings import (
        UpdateTableDiscoverySettingsUseCase,
    )
    from application.port.inbound.table_discovery_rule.create_table_discovery_rule import (
        CreateTableDiscoveryRuleUseCase,
    )
    from application.port.inbound.table_discovery_rule.delete_table_discovery_rule import (
        DeleteTableDiscoveryRuleUseCase,
    )
    from application.port.inbound.table_discovery_rule.list_table_discovery_rules import (
        ListTableDiscoveryRulesUseCase,
    )
    from application.port.inbound.table_discovery_rule.update_table_discovery_rule import (
        UpdateTableDiscoveryRuleUseCase,
    )
    from application.port.inbound.maintenance_run.get_maintenance_run import (
        GetMaintenanceRunUseCase,
    )
    from application.port.inbound.maintenance_run.list_maintenance_runs import (
        ListMaintenanceRunsUseCase,
    )
    from application.port.inbound.maintenance_run.process_maintenance_callback import (
        ProcessMaintenanceCallbackUseCase,
    )
    from application.port.inbound.table.exclude_table import (
        ExcludeTableUseCase,
    )
    from application.port.inbound.table.get_table import (
        GetTableUseCase,
    )
    from application.port.inbound.table.include_table import (
        IncludeTableUseCase,
    )
    from application.port.inbound.table.list_tables import (
        ListTablesUseCase,
    )
    from application.port.inbound.table.pause_table import (
        PauseTableUseCase,
    )
    from application.port.inbound.table.reset_table_selection import (
        ResetTableSelectionUseCase,
    )
    from application.port.inbound.table.resume_table import (
        ResumeTableUseCase,
    )
    from application.port.inbound.table.trigger_table_maintenance import (
        TriggerTableMaintenanceUseCase,
    )
    from application.port.inbound.table.update_table_settings import (
        UpdateTableSettingsUseCase,
    )
    from application.port.inbound.table_maintenance_preset.create_table_maintenance_preset import (
        CreateTableMaintenancePresetUseCase,
    )
    from application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset import (
        DeleteTableMaintenancePresetUseCase,
    )
    from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset import (
        GetTableMaintenancePresetUseCase,
    )
    from application.port.inbound.table_maintenance_preset.list_table_maintenance_presets import (
        ListTableMaintenancePresetsUseCase,
    )
    from application.port.inbound.table_maintenance_preset.update_table_maintenance_preset import (
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
    update_table_settings: UpdateTableSettingsUseCase
    pause_table: PauseTableUseCase
    resume_table: ResumeTableUseCase
    reset_table_selection: ResetTableSelectionUseCase
    include_table: IncludeTableUseCase
    exclude_table: ExcludeTableUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    list_maintenance_runs: ListMaintenanceRunsUseCase
    get_maintenance_run: GetMaintenanceRunUseCase
    process_maintenance_callback: ProcessMaintenanceCallbackUseCase
