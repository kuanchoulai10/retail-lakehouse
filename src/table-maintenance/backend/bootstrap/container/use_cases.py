"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.inbound.discovery.get_discovery_settings import (
        GetDiscoverySettingsUseCase,
    )
    from application.port.inbound.discovery.process_table_hint import (
        ProcessTableHintUseCase,
    )
    from application.port.inbound.discovery.sync_discovered_tables import (
        SyncDiscoveredTablesUseCase,
    )
    from application.port.inbound.discovery.update_discovery_settings import (
        UpdateDiscoverySettingsUseCase,
    )
    from application.port.inbound.discovery_rule.create_discovery_rule import (
        CreateDiscoveryRuleUseCase,
    )
    from application.port.inbound.discovery_rule.delete_discovery_rule import (
        DeleteDiscoveryRuleUseCase,
    )
    from application.port.inbound.discovery_rule.list_discovery_rules import (
        ListDiscoveryRulesUseCase,
    )
    from application.port.inbound.discovery_rule.update_discovery_rule import (
        UpdateDiscoveryRuleUseCase,
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
    from application.port.inbound.managed_table.exclude_managed_table import (
        ExcludeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.get_managed_table import (
        GetManagedTableUseCase,
    )
    from application.port.inbound.managed_table.include_managed_table import (
        IncludeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.list_managed_tables import (
        ListManagedTablesUseCase,
    )
    from application.port.inbound.managed_table.pause_managed_table import (
        PauseManagedTableUseCase,
    )
    from application.port.inbound.managed_table.reset_managed_table_selection import (
        ResetManagedTableSelectionUseCase,
    )
    from application.port.inbound.managed_table.resume_managed_table import (
        ResumeManagedTableUseCase,
    )
    from application.port.inbound.managed_table.trigger_maintenance import (
        TriggerMaintenanceUseCase,
    )
    from application.port.inbound.managed_table.update_managed_table_settings import (
        UpdateManagedTableSettingsUseCase,
    )
    from application.port.inbound.maintenance_run.create_maintenance_run import (
        CreateMaintenanceRunUseCase,
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
    from application.port.inbound.maintenance_run.record_maintenance_operation_result import (
        RecordMaintenanceOperationResultUseCase,
    )
    from application.port.inbound.reconcile.delete_maintenance_job import (
        DeleteMaintenanceJobUseCase,
    )
    from application.port.inbound.reconcile.get_maintenance_job_status import (
        GetMaintenanceJobStatusUseCase,
    )
    from application.port.inbound.reconcile.plan_table_maintenance import (
        PlanTableMaintenanceUseCase,
    )
    from application.port.inbound.reconcile.submit_maintenance_operation import (
        SubmitMaintenanceOperationUseCase,
    )


@dataclass(frozen=True)
class UseCases:
    """Hold one instance of every application service, keyed by use case."""

    get_discovery_settings: GetDiscoverySettingsUseCase
    process_table_hint: ProcessTableHintUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    update_discovery_settings: UpdateDiscoverySettingsUseCase
    create_discovery_rule: CreateDiscoveryRuleUseCase
    delete_discovery_rule: DeleteDiscoveryRuleUseCase
    list_discovery_rules: ListDiscoveryRulesUseCase
    update_discovery_rule: UpdateDiscoveryRuleUseCase
    create_table_maintenance_preset: CreateTableMaintenancePresetUseCase
    delete_table_maintenance_preset: DeleteTableMaintenancePresetUseCase
    get_table_maintenance_preset: GetTableMaintenancePresetUseCase
    list_table_maintenance_presets: ListTableMaintenancePresetsUseCase
    update_table_maintenance_preset: UpdateTableMaintenancePresetUseCase
    exclude_managed_table: ExcludeManagedTableUseCase
    get_managed_table: GetManagedTableUseCase
    include_managed_table: IncludeManagedTableUseCase
    list_managed_tables: ListManagedTablesUseCase
    pause_managed_table: PauseManagedTableUseCase
    reset_managed_table_selection: ResetManagedTableSelectionUseCase
    resume_managed_table: ResumeManagedTableUseCase
    trigger_maintenance: TriggerMaintenanceUseCase
    update_managed_table_settings: UpdateManagedTableSettingsUseCase
    create_maintenance_run: CreateMaintenanceRunUseCase
    get_maintenance_run: GetMaintenanceRunUseCase
    list_maintenance_runs: ListMaintenanceRunsUseCase
    process_maintenance_callback: ProcessMaintenanceCallbackUseCase
    record_maintenance_operation_result: RecordMaintenanceOperationResultUseCase
    delete_maintenance_job: DeleteMaintenanceJobUseCase
    get_maintenance_job_status: GetMaintenanceJobStatusUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
