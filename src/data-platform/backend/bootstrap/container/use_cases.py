"""Define the UseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ListCompactionCandidatesUseCase,
        ReleaseCompactionCandidatesUseCase,
    )
    from context.table_maintenance.application.port.inbound.compaction_round import (
        ScheduleCompactionRoundUseCase,
    )
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
    from context.table_maintenance.application.port.inbound.table_discovery_rules import (
        GetTableDiscoveryRulesUseCase,
        ListCoveredCatalogsUseCase,
        PreviewTableDiscoveryRulesUseCase,
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
        CreateTableMaintenanceRunUseCase,
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobPodsUseCase,
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

    list_covered_catalogs: ListCoveredCatalogsUseCase
    process_table_hint: ProcessTableHintUseCase
    sync_discovered_tables: SyncDiscoveredTablesUseCase
    get_table_discovery_rules: GetTableDiscoveryRulesUseCase
    replace_table_discovery_rules: ReplaceTableDiscoveryRulesUseCase
    preview_table_discovery_rules: PreviewTableDiscoveryRulesUseCase
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
    get_maintenance_job_pods: GetMaintenanceJobPodsUseCase
    plan_table_maintenance: PlanTableMaintenanceUseCase
    submit_maintenance_operation: SubmitMaintenanceOperationUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    record_table_reconciliation: RecordTableReconciliationUseCase
    release_compaction_candidates: ReleaseCompactionCandidatesUseCase
    list_compaction_candidates: ListCompactionCandidatesUseCase
    schedule_compaction_round: ScheduleCompactionRoundUseCase
