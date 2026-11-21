"""Define the WebUseCases bundle."""

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
        SetTablePriorityUseCase,
        TriggerTableMaintenanceUseCase,
        TriggerTableReconciliationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_policy import (
        CreateTableDiscoveryPolicyUseCase,
        DeleteTableDiscoveryPolicyUseCase,
        GetTableDiscoveryPolicyUseCase,
        GetTableDiscoveryPolicyVersionUseCase,
        ListTableDiscoveryPoliciesUseCase,
        UpdateTableDiscoveryPolicyUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
        AttachTableDiscoveryPolicyUseCase,
        DetachTableDiscoveryPolicyUseCase,
        ListTableDiscoveryPolicyAttachmentsUseCase,
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
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        GetPlatformSettingsUseCase,
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        GetTableReconciliationUseCase,
        ListTableReconciliationsUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every use case the web API calls; the composition root builds it."""

    list_table_discovery_policies: ListTableDiscoveryPoliciesUseCase
    create_table_discovery_policy: CreateTableDiscoveryPolicyUseCase
    get_table_discovery_policy: GetTableDiscoveryPolicyUseCase
    get_table_discovery_policy_version: GetTableDiscoveryPolicyVersionUseCase
    update_table_discovery_policy: UpdateTableDiscoveryPolicyUseCase
    delete_table_discovery_policy: DeleteTableDiscoveryPolicyUseCase
    attach_table_discovery_policy: AttachTableDiscoveryPolicyUseCase
    detach_table_discovery_policy: DetachTableDiscoveryPolicyUseCase
    list_table_discovery_policy_attachments: ListTableDiscoveryPolicyAttachmentsUseCase
    list_scanned_catalogs: ListScannedCatalogsUseCase
    list_table_maintenance_policies: ListTableMaintenancePoliciesUseCase
    create_table_maintenance_policy: CreateTableMaintenancePolicyUseCase
    get_table_maintenance_policy: GetTableMaintenancePolicyUseCase
    get_table_maintenance_policy_version: GetTableMaintenancePolicyVersionUseCase
    update_table_maintenance_policy: UpdateTableMaintenancePolicyUseCase
    delete_table_maintenance_policy: DeleteTableMaintenancePolicyUseCase
    attach_table_maintenance_policy: AttachTableMaintenancePolicyUseCase
    detach_table_maintenance_policy: DetachTableMaintenancePolicyUseCase
    list_table_maintenance_policy_attachments: ListTableMaintenancePolicyAttachmentsUseCase
    get_effective_policies: GetEffectivePoliciesUseCase
    list_tables: ListTablesUseCase
    get_table: GetTableUseCase
    get_table_current_metrics: GetTableCurrentMetricsUseCase
    get_table_metric_trends: GetTableMetricTrendsUseCase
    list_table_commits: ListTableCommitsUseCase
    list_table_metrics: ListTableMetricsUseCase
    set_table_priority: SetTablePriorityUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    get_table_reconciliation: GetTableReconciliationUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
    get_platform_settings: GetPlatformSettingsUseCase
