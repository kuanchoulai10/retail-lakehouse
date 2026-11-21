"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        GetTableCurrentMetricsUseCase,
        GetTableMetricTrendsUseCase,
        GetTableUseCase,
        ListTableCommitsUseCase,
        ListTableMetricsUseCase,
        ListTablesUseCase,
        PlanTableMaintenanceUseCase,
        ProcessTableHintUseCase,
        SetTablePriorityUseCase,
        SyncDiscoveredTablesUseCase,
        TriggerTableMaintenanceUseCase,
        TriggerTableReconciliationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_rules import (
        GetTableDiscoveryRulesUseCase,
        ListCoveredCatalogsUseCase,
        ReplaceTableDiscoveryRulesUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
        CreateTableMaintenancePolicyUseCase,
        DeleteTableMaintenancePolicyUseCase,
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
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunsUseCase,
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobPodsUseCase,
        GetMaintenanceJobStatusUseCase,
        GetPlatformSettingsUseCase,
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
        RaiseTableMaintenanceRunPriorityUseCase,
        RecordMaintenanceAttemptRunningUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SkipTableMaintenanceRunUseCase,
        SubmitMaintenanceOperationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        GetTableReconciliationUseCase,
        ListTableReconciliationsUseCase,
        RecordTableReconciliationUseCase,
    )


@dataclass(frozen=True)
class UseCases:
    """Hold one instance of every application service, keyed by use case."""

    list_covered_catalogs: ListCoveredCatalogsUseCase
    process_table_hint: ProcessTableHintUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    get_table_discovery_rules: GetTableDiscoveryRulesUseCase
    replace_table_discovery_rules: ReplaceTableDiscoveryRulesUseCase
    attach_table_maintenance_policy: AttachTableMaintenancePolicyUseCase
    detach_table_maintenance_policy: DetachTableMaintenancePolicyUseCase
    list_table_maintenance_policy_attachments: ListTableMaintenancePolicyAttachmentsUseCase
    resolve_applicable_table_maintenance_policy: ResolveApplicableTableMaintenancePolicyUseCase
    create_table_maintenance_policy: CreateTableMaintenancePolicyUseCase
    delete_table_maintenance_policy: DeleteTableMaintenancePolicyUseCase
    get_table_maintenance_policy: GetTableMaintenancePolicyUseCase
    get_table_maintenance_policy_version: GetTableMaintenancePolicyVersionUseCase
    list_table_maintenance_policies: ListTableMaintenancePoliciesUseCase
    update_table_maintenance_policy: UpdateTableMaintenancePolicyUseCase
    get_table: GetTableUseCase
    get_table_current_metrics: GetTableCurrentMetricsUseCase
    get_table_metric_trends: GetTableMetricTrendsUseCase
    list_table_commits: ListTableCommitsUseCase
    list_table_metrics: ListTableMetricsUseCase
    list_tables: ListTablesUseCase
    set_table_priority: SetTablePriorityUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
    create_table_maintenance_runs: CreateTableMaintenanceRunsUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    record_table_maintenance_operation_result: RecordTableMaintenanceOperationResultUseCase
    delete_maintenance_job: DeleteMaintenanceJobUseCase
    get_maintenance_job_status: GetMaintenanceJobStatusUseCase
    get_maintenance_job_pods: GetMaintenanceJobPodsUseCase
    record_maintenance_attempt_running: RecordMaintenanceAttemptRunningUseCase
    raise_table_maintenance_run_priority: RaiseTableMaintenanceRunPriorityUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    skip_table_maintenance_run: SkipTableMaintenanceRunUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
    get_table_reconciliation: GetTableReconciliationUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    record_table_reconciliation: RecordTableReconciliationUseCase
    get_platform_settings: GetPlatformSettingsUseCase
