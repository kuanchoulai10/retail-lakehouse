"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.catalog_discovery import ListScannedCatalogsUseCase
    from context.table_maintenance.application.port.inbound.table import (
        GetEffectivePoliciesUseCase,
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
    from context.table_maintenance.application.port.inbound.table_discovery_policy import (
        AttachTableDiscoveryPolicyUseCase,
        CreateTableDiscoveryPolicyUseCase,
        DeleteTableDiscoveryPolicyUseCase,
        DetachTableDiscoveryPolicyUseCase,
        GetTableDiscoveryPolicyUseCase,
        GetTableDiscoveryPolicyVersionUseCase,
        ListTableDiscoveryPoliciesUseCase,
        ListTableDiscoveryPolicyAttachmentsUseCase,
        SyncDiscoverySchedulesUseCase,
        UpdateTableDiscoveryPolicyUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
        AttachTableMaintenancePolicyUseCase,
        CreateTableMaintenancePolicyUseCase,
        DeleteTableMaintenancePolicyUseCase,
        DetachTableMaintenancePolicyUseCase,
        GetTableMaintenancePolicyUseCase,
        GetTableMaintenancePolicyVersionUseCase,
        ListTableMaintenancePoliciesUseCase,
        ListTableMaintenancePolicyAttachmentsUseCase,
        ResolveApplicableTableMaintenancePolicyUseCase,
        UpdateTableMaintenancePolicyUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CancelTableMaintenanceRunUseCase,
        CreateTableMaintenanceRunsUseCase,
        DeleteMaintenanceJobUseCase,
        ForwardTableMaintenanceResultUseCase,
        GetMaintenanceJobProcessesUseCase,
        GetMaintenanceJobStatusUseCase,
        GetPlatformSettingsUseCase,
        GetTableMaintenanceRunUseCase,
        IssueTableMaintenanceRunIdsUseCase,
        ListTableMaintenanceRunsUseCase,
        RaiseTableMaintenanceRunPriorityUseCase,
        RecordMaintenanceAttemptRunningUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SkipTableMaintenanceRunUseCase,
        SubmitMaintenanceOperationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        GetTableReconciliationUseCase,
        IssueTableReconciliationIdUseCase,
        ListTableReconciliationsUseCase,
        RecordTableReconciliationUseCase,
    )


@dataclass(frozen=True)
class UseCases:
    """Hold one instance of every application service, keyed by use case."""

    process_table_hint: ProcessTableHintUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    attach_table_maintenance_policy: AttachTableMaintenancePolicyUseCase
    detach_table_maintenance_policy: DetachTableMaintenancePolicyUseCase
    list_table_maintenance_policy_attachments: ListTableMaintenancePolicyAttachmentsUseCase
    resolve_applicable_table_maintenance_policy: ResolveApplicableTableMaintenancePolicyUseCase
    get_effective_policies: GetEffectivePoliciesUseCase
    create_table_maintenance_policy: CreateTableMaintenancePolicyUseCase
    delete_table_maintenance_policy: DeleteTableMaintenancePolicyUseCase
    get_table_maintenance_policy: GetTableMaintenancePolicyUseCase
    get_table_maintenance_policy_version: GetTableMaintenancePolicyVersionUseCase
    list_table_discovery_policies: ListTableDiscoveryPoliciesUseCase
    create_table_discovery_policy: CreateTableDiscoveryPolicyUseCase
    get_table_discovery_policy: GetTableDiscoveryPolicyUseCase
    get_table_discovery_policy_version: GetTableDiscoveryPolicyVersionUseCase
    update_table_discovery_policy: UpdateTableDiscoveryPolicyUseCase
    delete_table_discovery_policy: DeleteTableDiscoveryPolicyUseCase
    attach_table_discovery_policy: AttachTableDiscoveryPolicyUseCase
    detach_table_discovery_policy: DetachTableDiscoveryPolicyUseCase
    list_table_discovery_policy_attachments: ListTableDiscoveryPolicyAttachmentsUseCase
    sync_discovery_schedules: SyncDiscoverySchedulesUseCase
    list_scanned_catalogs: ListScannedCatalogsUseCase
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
    forward_table_maintenance_result: ForwardTableMaintenanceResultUseCase
    record_table_maintenance_operation_result: RecordTableMaintenanceOperationResultUseCase
    delete_maintenance_job: DeleteMaintenanceJobUseCase
    get_maintenance_job_status: GetMaintenanceJobStatusUseCase
    get_maintenance_job_processes: GetMaintenanceJobProcessesUseCase
    record_maintenance_attempt_running: RecordMaintenanceAttemptRunningUseCase
    raise_table_maintenance_run_priority: RaiseTableMaintenanceRunPriorityUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    skip_table_maintenance_run: SkipTableMaintenanceRunUseCase
    cancel_table_maintenance_run: CancelTableMaintenanceRunUseCase
    issue_table_maintenance_run_ids: IssueTableMaintenanceRunIdsUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
    get_table_reconciliation: GetTableReconciliationUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    record_table_reconciliation: RecordTableReconciliationUseCase
    issue_table_reconciliation_id: IssueTableReconciliationIdUseCase
    get_platform_settings: GetPlatformSettingsUseCase
