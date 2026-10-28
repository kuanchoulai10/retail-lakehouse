"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.inbound.table_discovery_settings.get_table_discovery_settings import (
        GetTableDiscoverySettingsUseCase,
    )
    from application.port.inbound.table.process_table_hint import (
        ProcessTableHintUseCase,
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
    from application.port.inbound.table_maintenance_run.create_table_maintenance_run import (
        CreateTableMaintenanceRunUseCase,
    )
    from application.port.inbound.table_maintenance_run.get_table_maintenance_run import (
        GetTableMaintenanceRunUseCase,
    )
    from application.port.inbound.table_maintenance_run.list_table_maintenance_runs import (
        ListTableMaintenanceRunsUseCase,
    )
    from application.port.inbound.table_maintenance_run.process_table_maintenance_callback import (
        ProcessTableMaintenanceCallbackUseCase,
    )
    from application.port.inbound.table_maintenance_run.record_table_maintenance_operation_result import (
        RecordTableMaintenanceOperationResultUseCase,
    )
    from application.port.inbound.table_maintenance_run.delete_maintenance_job import (
        DeleteMaintenanceJobUseCase,
    )
    from application.port.inbound.table_maintenance_run.get_maintenance_job_status import (
        GetMaintenanceJobStatusUseCase,
    )
    from application.port.inbound.table.plan_table_maintenance import (
        PlanTableMaintenanceUseCase,
    )
    from application.port.inbound.table_maintenance_run.submit_maintenance_operation import (
        SubmitMaintenanceOperationUseCase,
    )


@dataclass(frozen=True)
class UseCases:
    """Hold one instance of every application service, keyed by use case."""

    get_table_discovery_settings: GetTableDiscoverySettingsUseCase
    process_table_hint: ProcessTableHintUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    update_table_discovery_settings: UpdateTableDiscoverySettingsUseCase
    create_table_discovery_rule: CreateTableDiscoveryRuleUseCase
    delete_table_discovery_rule: DeleteTableDiscoveryRuleUseCase
    list_table_discovery_rules: ListTableDiscoveryRulesUseCase
    update_table_discovery_rule: UpdateTableDiscoveryRuleUseCase
    create_table_maintenance_preset: CreateTableMaintenancePresetUseCase
    delete_table_maintenance_preset: DeleteTableMaintenancePresetUseCase
    get_table_maintenance_preset: GetTableMaintenancePresetUseCase
    list_table_maintenance_presets: ListTableMaintenancePresetsUseCase
    update_table_maintenance_preset: UpdateTableMaintenancePresetUseCase
    exclude_table: ExcludeTableUseCase
    get_table: GetTableUseCase
    include_table: IncludeTableUseCase
    list_tables: ListTablesUseCase
    pause_table: PauseTableUseCase
    reset_table_selection: ResetTableSelectionUseCase
    resume_table: ResumeTableUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    update_table_settings: UpdateTableSettingsUseCase
    create_table_maintenance_run: CreateTableMaintenanceRunUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    record_table_maintenance_operation_result: (
        RecordTableMaintenanceOperationResultUseCase
    )
    delete_maintenance_job: DeleteMaintenanceJobUseCase
    get_maintenance_job_status: GetMaintenanceJobStatusUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
