"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        GetTableHealthUseCase,
        GetTableStorageUseCase,
        GetTableUseCase,
        ListTableCommitsUseCase,
        ListTablesUseCase,
        PlanTableMaintenanceUseCase,
        ProcessTableHintUseCase,
        SyncDiscoveredTablesUseCase,
        TriggerTableMaintenanceUseCase,
        TriggerTableReconciliationUseCase,
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
    from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
        CreateTableMaintenancePolicyUseCase,
        DeleteTableMaintenancePolicyUseCase,
        EnsureDefaultTableMaintenancePolicyUseCase,
        GetTableMaintenancePolicyUseCase,
        GetTableMaintenancePolicyVersionUseCase,
        ListTableMaintenancePoliciesUseCase,
        UpdateTableMaintenancePolicyUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        AttachTableMaintenancePolicyUseCase,
        DetachTableMaintenancePolicyUseCase,
        ListTableMaintenancePolicyAttachmentsUseCase,
        ResolveApplicableTableMaintenancePolicyUseCase,
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
    attach_table_maintenance_policy: AttachTableMaintenancePolicyUseCase
    detach_table_maintenance_policy: DetachTableMaintenancePolicyUseCase
    list_table_maintenance_policy_attachments: ListTableMaintenancePolicyAttachmentsUseCase
    resolve_applicable_table_maintenance_policy: ResolveApplicableTableMaintenancePolicyUseCase
    create_table_maintenance_policy: CreateTableMaintenancePolicyUseCase
    delete_table_maintenance_policy: DeleteTableMaintenancePolicyUseCase
    ensure_default_table_maintenance_policy: EnsureDefaultTableMaintenancePolicyUseCase
    get_table_maintenance_policy: GetTableMaintenancePolicyUseCase
    get_table_maintenance_policy_version: GetTableMaintenancePolicyVersionUseCase
    list_table_maintenance_policies: ListTableMaintenancePoliciesUseCase
    update_table_maintenance_policy: UpdateTableMaintenancePolicyUseCase
    get_table: GetTableUseCase
    get_table_health: GetTableHealthUseCase
    get_table_storage: GetTableStorageUseCase
    list_table_commits: ListTableCommitsUseCase
    list_tables: ListTablesUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
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
