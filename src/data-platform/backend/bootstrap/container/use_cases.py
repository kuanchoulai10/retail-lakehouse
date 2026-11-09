"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        ExcludeTableUseCase,
        GetTableHealthUseCase,
        GetTableStorageUseCase,
        GetTableUseCase,
        IncludeTableUseCase,
        ListTableCommitsUseCase,
        ListTablesUseCase,
        PauseTableUseCase,
        PlanTableMaintenanceUseCase,
        ProcessTableHintUseCase,
        ResetTableSelectionUseCase,
        ResumeTableUseCase,
        SyncDiscoveredTablesUseCase,
        TriggerTableMaintenanceUseCase,
        TriggerTableReconciliationUseCase,
        UpdateTableSettingsUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_rule import (
        CreateTableDiscoveryRuleUseCase,
        DeleteTableDiscoveryRuleUseCase,
        ListTableDiscoveryRulesUseCase,
        UpdateTableDiscoveryRuleUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_settings import (
        GetTableDiscoverySettingsUseCase,
        ListCoveredCatalogsUseCase,
        UpdateTableDiscoverySettingsUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
        CreateTableMaintenancePresetUseCase,
        DeleteTableMaintenancePresetUseCase,
        GetTableMaintenancePresetUseCase,
        ListTableMaintenancePresetsUseCase,
        UpdateTableMaintenancePresetUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunUseCase,
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobStatusUseCase,
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SubmitMaintenanceOperationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        ListTableReconciliationsUseCase,
        RecordTableReconciliationUseCase,
    )


@dataclass(frozen=True)
class UseCases:
    """Hold one instance of every application service, keyed by use case."""

    get_table_discovery_settings: GetTableDiscoverySettingsUseCase
    list_covered_catalogs: ListCoveredCatalogsUseCase
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
    get_table_health: GetTableHealthUseCase
    get_table_storage: GetTableStorageUseCase
    list_table_commits: ListTableCommitsUseCase
    include_table: IncludeTableUseCase
    list_tables: ListTablesUseCase
    pause_table: PauseTableUseCase
    reset_table_selection: ResetTableSelectionUseCase
    resume_table: ResumeTableUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
    update_table_settings: UpdateTableSettingsUseCase
    create_table_maintenance_run: CreateTableMaintenanceRunUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    record_table_maintenance_operation_result: RecordTableMaintenanceOperationResultUseCase
    delete_maintenance_job: DeleteMaintenanceJobUseCase
    get_maintenance_job_status: GetMaintenanceJobStatusUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    record_table_reconciliation: RecordTableReconciliationUseCase
