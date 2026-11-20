"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bootstrap.container.use_cases import UseCases
from context.table_maintenance.application.domain.model.table import DEFAULT_OPERATION_COOLDOWNS
from context.table_maintenance.application.service.table import (
    GetTableCurrentMetricsService,
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
from context.table_maintenance.application.service.table_discovery_rules import (
    GetTableDiscoveryRulesService,
    ListCoveredCatalogsService,
    ReplaceTableDiscoveryRulesService,
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
    CreateTableMaintenanceRunService,
    DeleteMaintenanceJobService,
    GetMaintenanceJobPodsService,
    GetMaintenanceJobStatusService,
    GetPlatformSettingsService,
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
    ProcessTableMaintenanceCallbackService,
    RaiseTableMaintenanceRunPriorityService,
    RecordMaintenanceAttemptRunningService,
    RecordTableMaintenanceOperationResultService,
    SubmitMaintenanceOperationService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from bootstrap.container.gateways import Gateways
    from bootstrap.container.repositories import Repositories
    from context.table_maintenance.application.domain.model.shared import ComputeSize, PlatformSettings, SizeMemory
    from context.table_maintenance.application.domain.model.table import OperationCooldowns


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_use_cases(
    repos: Repositories,
    gateways: Gateways,
    *,
    platform_settings: PlatformSettings,
    clock: Callable[[], datetime] = _utc_now,
    catalog_names: Sequence[str] = (),
    size_memory: Mapping[ComputeSize, SizeMemory] | None = None,
    cooldowns: OperationCooldowns = DEFAULT_OPERATION_COOLDOWNS,
) -> UseCases:
    """Build every application service on the given repositories and gateways.

    ``size_memory`` is the memory each compute size runs with; without it no operation is ever
    stepped down to a smaller size. ``cooldowns`` are the cooldown of each operation and the cap where
    the doubling of a failing operation's cooldown stops. ``platform_settings`` are the values the platform
    settings page lists; every caller gives them, so none shows defaults by accident.
    """
    tables = repos.tables
    rules = repos.table_discovery_rules
    policies = repos.table_maintenance_policies
    attachments = repos.table_maintenance_policy_attachments
    runs = repos.table_maintenance_runs
    reconciliations = repos.table_reconciliations
    discoveries = repos.catalog_discoveries
    catalog = gateways.read_table_metadata
    table_changes = gateways.send_table_change
    resolve_applicable_policy = ResolveApplicableTableMaintenancePolicyService(policies, attachments, catalog, tables)
    return UseCases(
        list_covered_catalogs=ListCoveredCatalogsService(catalog_names),
        process_table_hint=ProcessTableHintService(
            tables,
            rules,
            catalog,
            table_changes,
            gateways.send_discovery_request,
            clock=clock,
        ),
        sync_discovered_tables=SyncDiscoveredTablesService(
            tables, rules, discoveries, catalog, table_changes, clock=clock
        ),
        get_table_discovery_rules=GetTableDiscoveryRulesService(rules),
        replace_table_discovery_rules=ReplaceTableDiscoveryRulesService(
            rules, gateways.send_discovery_request, catalog_names, clock=clock
        ),
        attach_table_maintenance_policy=AttachTableMaintenancePolicyService(
            policies, attachments, catalog, tables, table_changes, clock=clock
        ),
        detach_table_maintenance_policy=DetachTableMaintenancePolicyService(
            policies, attachments, catalog, tables, table_changes
        ),
        list_table_maintenance_policy_attachments=ListTableMaintenancePolicyAttachmentsService(
            policies, attachments, catalog, tables
        ),
        resolve_applicable_table_maintenance_policy=resolve_applicable_policy,
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
        list_table_commits=ListTableCommitsService(tables, catalog),
        list_table_metrics=ListTableMetricsService(tables, repos.table_metrics),
        list_tables=ListTablesService(tables, discoveries, policies),
        set_table_priority=SetTablePriorityService(tables, clock=clock),
        trigger_table_maintenance=TriggerTableMaintenanceService(tables, table_changes),
        trigger_table_reconciliation=TriggerTableReconciliationService(tables, table_changes),
        create_table_maintenance_run=CreateTableMaintenanceRunService(runs, tables),
        get_table_maintenance_run=GetTableMaintenanceRunService(runs),
        list_table_maintenance_runs=ListTableMaintenanceRunsService(runs),
        process_table_maintenance_callback=ProcessTableMaintenanceCallbackService(
            runs, gateways.send_maintenance_result
        ),
        record_table_maintenance_operation_result=RecordTableMaintenanceOperationResultService(
            runs,
            tables,
            gateways.read_maintenance_job_evidence,
            gateways.read_maintenance_event_log,
            resolve_applicable_policy,
            size_memory=size_memory or {},
        ),
        delete_maintenance_job=DeleteMaintenanceJobService(gateways.delete_maintenance_job),
        get_maintenance_job_status=GetMaintenanceJobStatusService(
            gateways.read_maintenance_job, gateways.read_maintenance_job_pods
        ),
        get_maintenance_job_pods=GetMaintenanceJobPodsService(gateways.read_maintenance_job_pods),
        record_maintenance_attempt_running=RecordMaintenanceAttemptRunningService(runs),
        raise_table_maintenance_run_priority=RaiseTableMaintenanceRunPriorityService(runs, tables),
        plan_table_maintenance=PlanTableMaintenanceService(
            tables,
            catalog,
            resolve_applicable_policy,
            metrics_store=repos.table_metrics,
            cooldowns=cooldowns,
        ),
        get_platform_settings=GetPlatformSettingsService(platform_settings),
        list_table_reconciliations=ListTableReconciliationsService(reconciliations, policies),
        record_table_reconciliation=RecordTableReconciliationService(reconciliations),
        submit_maintenance_operation=SubmitMaintenanceOperationService(runs, tables, gateways.submit_maintenance_job),
    )
