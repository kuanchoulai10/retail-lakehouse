"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bootstrap.container.use_cases import UseCases
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_OPERATION_COOLDOWNS,
    DEFAULT_PARTITION_SELECTION_SETTINGS,
)
from context.table_maintenance.application.service.catalog_discovery import ListScannedCatalogsService
from context.table_maintenance.application.service.table import (
    GetEffectivePoliciesService,
    GetTableCurrentMetricsService,
    GetTableMetricTrendsService,
    GetTableService,
    ListTableCommitsService,
    ListTableMetricsService,
    ListTablesService,
    PlanTableMaintenanceService,
    ProcessTableHintService,
    SetTablePriorityService,
    SyncDiscoveredTablesService,
    TriggerTableMaintenanceService,
    TriggerTableReconciliationService,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    AttachTableDiscoveryPolicyService,
    CreateTableDiscoveryPolicyService,
    DeleteTableDiscoveryPolicyService,
    DetachTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    ListTableDiscoveryPolicyAttachmentsService,
    SyncDiscoverySchedulesService,
    UpdateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    GetTableMaintenancePolicyService,
    GetTableMaintenancePolicyVersionService,
    ListTableMaintenancePoliciesService,
    UpdateTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
    ListTableMaintenancePolicyAttachmentsService,
    ResolveApplicableTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CancelTableMaintenanceRunService,
    CreateTableMaintenanceRunsService,
    DeleteMaintenanceJobService,
    ForwardTableMaintenanceResultService,
    GetMaintenanceJobProcessesService,
    GetMaintenanceJobStatusService,
    GetPlatformSettingsService,
    GetTableMaintenanceRunService,
    IssueTableMaintenanceRunIdsService,
    ListTableMaintenanceRunsService,
    RaiseTableMaintenanceRunPriorityService,
    RecordMaintenanceAttemptRunningService,
    RecordTableMaintenanceOperationResultService,
    SkipTableMaintenanceRunService,
    SubmitMaintenanceOperationService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    GetTableReconciliationService,
    IssueTableReconciliationIdService,
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from bootstrap.container.gateways import Gateways
    from bootstrap.container.repositories import Repositories
    from context.table_maintenance.application.domain.model.shared import ComputeSize, PlatformSettings, SizeMemory
    from context.table_maintenance.application.domain.model.table import (
        OperationCooldowns,
        PartitionSelectionSettings,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_use_cases(
    repos: Repositories,
    gateways: Gateways,
    *,
    platform_settings: PlatformSettings,
    clock: Callable[[], datetime] = _utc_now,
    size_memory: Mapping[ComputeSize, SizeMemory] | None = None,
    cooldowns: OperationCooldowns = DEFAULT_OPERATION_COOLDOWNS,
    partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS,
) -> UseCases:
    """Build every application service on the given repositories and gateways.

    ``size_memory`` is the memory each compute size runs with; without it no operation is ever
    stepped down to a smaller size. ``cooldowns`` are the cooldown of each operation and the cap where
    the doubling of a failing operation's cooldown stops. ``partition_selection`` is how a scheduled compaction
    chooses the partitions of one job. ``platform_settings`` are the values the platform settings page lists;
    every caller gives them, so none shows defaults by accident.
    """
    tables = repos.tables
    discovery_policies = repos.table_discovery_policies
    placements = repos.policy_placements
    catalogs, namespaces = repos.catalogs, repos.namespaces
    policies = repos.table_maintenance_policies
    attachments = repos.table_maintenance_policy_attachments
    runs = repos.table_maintenance_runs
    reconciliations = repos.table_reconciliations
    discoveries = repos.catalog_discoveries
    catalog = gateways.read_table_metadata
    table_changes = gateways.send_table_change
    discovery_requests = gateways.send_discovery_request
    discovery_schedules = gateways.sync_discovery_schedules
    resolve_applicable_policy = ResolveApplicableTableMaintenancePolicyService(policies, attachments, catalog, tables)
    return UseCases(
        process_table_hint=ProcessTableHintService(
            tables,
            discovery_policies,
            catalogs,
            namespaces,
            catalog,
            table_changes,
            gateways.send_discovery_request,
            clock=clock,
        ),
        sync_discovered_tables=SyncDiscoveredTablesService(
            tables,
            discovery_policies,
            catalogs,
            namespaces,
            placements,
            discoveries,
            catalog,
            table_changes,
            clock=clock,
        ),
        list_table_discovery_policies=ListTableDiscoveryPoliciesService(discovery_policies, placements),
        create_table_discovery_policy=CreateTableDiscoveryPolicyService(discovery_policies, clock=clock),
        get_table_discovery_policy=GetTableDiscoveryPolicyService(discovery_policies),
        get_table_discovery_policy_version=GetTableDiscoveryPolicyVersionService(discovery_policies),
        update_table_discovery_policy=UpdateTableDiscoveryPolicyService(
            discovery_policies, placements, discovery_requests, clock=clock
        ),
        delete_table_discovery_policy=DeleteTableDiscoveryPolicyService(discovery_policies, placements),
        attach_table_discovery_policy=AttachTableDiscoveryPolicyService(
            discovery_policies, catalogs, namespaces, tables, catalog, discovery_requests, clock=clock
        ),
        detach_table_discovery_policy=DetachTableDiscoveryPolicyService(
            discovery_policies, catalogs, namespaces, tables, discovery_requests, clock=clock
        ),
        list_table_discovery_policy_attachments=ListTableDiscoveryPolicyAttachmentsService(
            discovery_policies, placements, catalog, tables
        ),
        sync_discovery_schedules=SyncDiscoverySchedulesService(
            placements, tables, discovery_requests, discovery_schedules
        ),
        list_scanned_catalogs=ListScannedCatalogsService(placements, tables, discoveries),
        attach_table_maintenance_policy=AttachTableMaintenancePolicyService(
            policies, attachments, catalog, tables, table_changes, clock=clock
        ),
        detach_table_maintenance_policy=DetachTableMaintenancePolicyService(
            policies, attachments, tables, table_changes
        ),
        list_table_maintenance_policy_attachments=ListTableMaintenancePolicyAttachmentsService(
            policies, attachments, catalog, tables
        ),
        resolve_applicable_table_maintenance_policy=resolve_applicable_policy,
        get_effective_policies=GetEffectivePoliciesService(
            policies, attachments, discovery_policies, catalogs, namespaces, catalog, tables
        ),
        create_table_maintenance_policy=CreateTableMaintenancePolicyService(policies, clock=clock),
        delete_table_maintenance_policy=DeleteTableMaintenancePolicyService(policies, attachments),
        get_table_maintenance_policy=GetTableMaintenancePolicyService(policies),
        get_table_maintenance_policy_version=GetTableMaintenancePolicyVersionService(policies),
        list_table_maintenance_policies=ListTableMaintenancePoliciesService(policies, attachments),
        update_table_maintenance_policy=UpdateTableMaintenancePolicyService(
            policies, attachments, tables, table_changes, clock=clock
        ),
        get_table=GetTableService(tables, discoveries, policies),
        get_table_current_metrics=GetTableCurrentMetricsService(tables, repos.table_metrics),
        get_table_metric_trends=GetTableMetricTrendsService(tables, gateways.read_table_metric_history),
        list_table_commits=ListTableCommitsService(tables, catalog),
        list_table_metrics=ListTableMetricsService(tables, repos.table_metrics),
        list_tables=ListTablesService(tables, discoveries, policies),
        set_table_priority=SetTablePriorityService(tables, clock=clock),
        trigger_table_maintenance=TriggerTableMaintenanceService(tables, table_changes),
        trigger_table_reconciliation=TriggerTableReconciliationService(tables, table_changes),
        create_table_maintenance_runs=CreateTableMaintenanceRunsService(runs, tables),
        get_table_maintenance_run=GetTableMaintenanceRunService(runs),
        list_table_maintenance_runs=ListTableMaintenanceRunsService(runs),
        forward_table_maintenance_result=ForwardTableMaintenanceResultService(runs, gateways.send_maintenance_result),
        record_table_maintenance_operation_result=RecordTableMaintenanceOperationResultService(
            runs,
            tables,
            gateways.read_maintenance_job_evidence,
            gateways.read_maintenance_event_log,
            size_memory=size_memory or {},
        ),
        delete_maintenance_job=DeleteMaintenanceJobService(runs, gateways.delete_maintenance_job),
        get_maintenance_job_status=GetMaintenanceJobStatusService(
            runs, gateways.read_maintenance_job, gateways.read_maintenance_job_processes
        ),
        get_maintenance_job_processes=GetMaintenanceJobProcessesService(runs, gateways.read_maintenance_job_processes),
        record_maintenance_attempt_running=RecordMaintenanceAttemptRunningService(runs),
        raise_table_maintenance_run_priority=RaiseTableMaintenanceRunPriorityService(runs, tables),
        plan_table_maintenance=PlanTableMaintenanceService(
            tables,
            catalog,
            resolve_applicable_policy,
            metrics_store=repos.table_metrics,
            cooldowns=cooldowns,
            partition_selection=partition_selection,
        ),
        get_platform_settings=GetPlatformSettingsService(platform_settings),
        get_table_reconciliation=GetTableReconciliationService(reconciliations, policies),
        list_table_reconciliations=ListTableReconciliationsService(reconciliations, policies),
        record_table_reconciliation=RecordTableReconciliationService(reconciliations),
        skip_table_maintenance_run=SkipTableMaintenanceRunService(runs),
        cancel_table_maintenance_run=CancelTableMaintenanceRunService(runs),
        issue_table_maintenance_run_ids=IssueTableMaintenanceRunIdsService(),
        issue_table_reconciliation_id=IssueTableReconciliationIdService(),
        submit_maintenance_operation=SubmitMaintenanceOperationService(runs, tables, gateways.submit_maintenance_job),
    )
