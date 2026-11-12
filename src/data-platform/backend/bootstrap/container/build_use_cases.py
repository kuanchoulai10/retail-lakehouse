"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bootstrap.container.use_cases import UseCases
from context.table_maintenance.application.service.table import (
    GetTableHealthService,
    GetTableService,
    GetTableStorageService,
    ListTableCommitsService,
    ListTablesService,
    PlanTableMaintenanceService,
    ProcessTableHintService,
    SyncDiscoveredTablesService,
    TriggerTableMaintenanceService,
    TriggerTableReconciliationService,
)
from context.table_maintenance.application.service.table_discovery_rules import (
    GetTableDiscoveryRulesService,
    ListCoveredCatalogsService,
    PreviewTableDiscoveryRulesService,
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
    GetTableMaintenanceRunService,
    ListTableMaintenanceRunsService,
    ProcessTableMaintenanceCallbackService,
    RecordTableMaintenanceOperationResultService,
    SubmitMaintenanceOperationService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from bootstrap.container.gateways import Gateways
    from bootstrap.container.repositories import Repositories


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_use_cases(
    repos: Repositories,
    gateways: Gateways,
    *,
    clock: Callable[[], datetime] = _utc_now,
    catalog_names: Sequence[str] = (),
) -> UseCases:
    """Build every application service on the given repositories and gateways."""
    tables = repos.tables
    rules = repos.table_discovery_rules
    policies = repos.table_maintenance_policies
    attachments = repos.table_maintenance_policy_attachments
    runs = repos.table_maintenance_runs
    reconciliations = repos.table_reconciliations
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
        sync_discovered_tables=SyncDiscoveredTablesService(tables, rules, catalog, table_changes, clock=clock),
        get_table_discovery_rules=GetTableDiscoveryRulesService(rules),
        replace_table_discovery_rules=ReplaceTableDiscoveryRulesService(
            rules, gateways.send_discovery_request, catalog_names, clock=clock
        ),
        preview_table_discovery_rules=PreviewTableDiscoveryRulesService(catalog, catalog_names, clock=clock),
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
        get_table=GetTableService(tables),
        get_table_health=GetTableHealthService(tables, catalog, resolve_applicable_policy, clock=clock),
        get_table_storage=GetTableStorageService(tables, catalog, runs, clock=clock),
        list_table_commits=ListTableCommitsService(tables, catalog),
        list_tables=ListTablesService(tables),
        trigger_table_maintenance=TriggerTableMaintenanceService(tables, table_changes),
        trigger_table_reconciliation=TriggerTableReconciliationService(tables, table_changes),
        create_table_maintenance_run=CreateTableMaintenanceRunService(runs, tables),
        get_table_maintenance_run=GetTableMaintenanceRunService(runs),
        list_table_maintenance_runs=ListTableMaintenanceRunsService(runs),
        process_table_maintenance_callback=ProcessTableMaintenanceCallbackService(
            runs, gateways.send_maintenance_result
        ),
        record_table_maintenance_operation_result=RecordTableMaintenanceOperationResultService(runs, tables),
        delete_maintenance_job=DeleteMaintenanceJobService(gateways.delete_maintenance_job),
        get_maintenance_job_status=GetMaintenanceJobStatusService(gateways.read_maintenance_job),
        get_maintenance_job_pods=GetMaintenanceJobPodsService(gateways.read_maintenance_job_pods),
        plan_table_maintenance=PlanTableMaintenanceService(tables, catalog, resolve_applicable_policy),
        list_table_reconciliations=ListTableReconciliationsService(reconciliations),
        record_table_reconciliation=RecordTableReconciliationService(reconciliations),
        submit_maintenance_operation=SubmitMaintenanceOperationService(runs, tables, gateways.submit_maintenance_job),
    )
