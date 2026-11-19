"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ListCompactionCandidatesUseCase,
    )
    from context.table_maintenance.application.port.inbound.compaction_round import (
        GetCompactionRoundUseCase,
        GetPlatformSettingsUseCase,
        GetSchedulerSettingsUseCase,
        ListCompactionRoundsUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        GetTableHealthUseCase,
        GetTableStorageUseCase,
        GetTableUseCase,
        ListTableCommitsUseCase,
        ListTablesUseCase,
        SetTablePriorityUseCase,
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
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        ListTableReconciliationsUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every use case the web API calls; the composition root builds it."""

    get_table_discovery_rules: GetTableDiscoveryRulesUseCase
    replace_table_discovery_rules: ReplaceTableDiscoveryRulesUseCase
    list_covered_catalogs: ListCoveredCatalogsUseCase
    list_table_maintenance_policies: ListTableMaintenancePoliciesUseCase
    create_table_maintenance_policy: CreateTableMaintenancePolicyUseCase
    get_table_maintenance_policy: GetTableMaintenancePolicyUseCase
    get_table_maintenance_policy_version: GetTableMaintenancePolicyVersionUseCase
    update_table_maintenance_policy: UpdateTableMaintenancePolicyUseCase
    delete_table_maintenance_policy: DeleteTableMaintenancePolicyUseCase
    attach_table_maintenance_policy: AttachTableMaintenancePolicyUseCase
    detach_table_maintenance_policy: DetachTableMaintenancePolicyUseCase
    list_table_maintenance_policy_attachments: ListTableMaintenancePolicyAttachmentsUseCase
    resolve_applicable_table_maintenance_policy: ResolveApplicableTableMaintenancePolicyUseCase
    list_tables: ListTablesUseCase
    get_table: GetTableUseCase
    get_table_health: GetTableHealthUseCase
    get_table_storage: GetTableStorageUseCase
    list_table_commits: ListTableCommitsUseCase
    set_table_priority: SetTablePriorityUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    list_compaction_candidates: ListCompactionCandidatesUseCase
    list_compaction_rounds: ListCompactionRoundsUseCase
    get_compaction_round: GetCompactionRoundUseCase
    get_scheduler_settings: GetSchedulerSettingsUseCase
    get_platform_settings: GetPlatformSettingsUseCase
