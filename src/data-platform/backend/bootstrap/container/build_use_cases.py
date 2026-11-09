"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bootstrap.container.use_cases import UseCases
from context.table_maintenance.application.service.table import (
    ExcludeTableService,
    GetTableHealthService,
    GetTableService,
    GetTableStorageService,
    IncludeTableService,
    ListTableCommitsService,
    ListTablesService,
    PauseTableService,
    PlanTableMaintenanceService,
    ProcessTableHintService,
    ResetTableSelectionService,
    ResumeTableService,
    SyncDiscoveredTablesService,
    TriggerTableMaintenanceService,
    TriggerTableReconciliationService,
    UpdateTableSettingsService,
)
from context.table_maintenance.application.service.table_discovery_rule import (
    CreateTableDiscoveryRuleService,
    DeleteTableDiscoveryRuleService,
    ListTableDiscoveryRulesService,
    UpdateTableDiscoveryRuleService,
)
from context.table_maintenance.application.service.table_discovery_settings import (
    GetTableDiscoverySettingsService,
    ListCoveredCatalogsService,
    UpdateTableDiscoverySettingsService,
)
from context.table_maintenance.application.service.table_maintenance_preset import (
    CreateTableMaintenancePresetService,
    DeleteTableMaintenancePresetService,
    GetTableMaintenancePresetService,
    ListTableMaintenancePresetsService,
    UpdateTableMaintenancePresetService,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    CreateTableMaintenanceRunService,
    DeleteMaintenanceJobService,
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
    presets = repos.table_maintenance_presets
    runs = repos.table_maintenance_runs
    discovery = repos.table_discovery_settings
    reconciliations = repos.table_reconciliations
    catalog = gateways.read_table_metadata
    table_changes = gateways.send_table_change
    return UseCases(
        get_table_discovery_settings=GetTableDiscoverySettingsService(discovery),
        list_covered_catalogs=ListCoveredCatalogsService(catalog_names),
        process_table_hint=ProcessTableHintService(
            tables,
            rules,
            presets,
            discovery,
            catalog,
            table_changes,
            gateways.send_discovery_request,
            clock=clock,
        ),
        sync_discovered_tables=SyncDiscoveredTablesService(
            tables, rules, presets, discovery, catalog, table_changes, clock=clock
        ),
        update_table_discovery_settings=UpdateTableDiscoverySettingsService(
            discovery, gateways.update_table_discovery_schedule, clock=clock
        ),
        create_table_discovery_rule=CreateTableDiscoveryRuleService(rules, presets, clock=clock),
        delete_table_discovery_rule=DeleteTableDiscoveryRuleService(rules),
        list_table_discovery_rules=ListTableDiscoveryRulesService(rules),
        update_table_discovery_rule=UpdateTableDiscoveryRuleService(rules, presets, clock=clock),
        create_table_maintenance_preset=CreateTableMaintenancePresetService(presets, clock=clock),
        delete_table_maintenance_preset=DeleteTableMaintenancePresetService(presets, rules),
        get_table_maintenance_preset=GetTableMaintenancePresetService(presets),
        list_table_maintenance_presets=ListTableMaintenancePresetsService(presets),
        update_table_maintenance_preset=UpdateTableMaintenancePresetService(presets, clock=clock),
        exclude_table=ExcludeTableService(tables, catalog, table_changes, clock=clock),
        get_table=GetTableService(tables),
        get_table_health=GetTableHealthService(tables, catalog, clock=clock),
        get_table_storage=GetTableStorageService(tables, catalog, runs, clock=clock),
        list_table_commits=ListTableCommitsService(tables, catalog),
        include_table=IncludeTableService(tables, presets, catalog, table_changes, clock=clock),
        list_tables=ListTablesService(tables),
        pause_table=PauseTableService(tables, table_changes, clock=clock),
        reset_table_selection=ResetTableSelectionService(tables, rules, presets, table_changes, clock=clock),
        resume_table=ResumeTableService(tables, table_changes, clock=clock),
        trigger_table_maintenance=TriggerTableMaintenanceService(tables, table_changes),
        trigger_table_reconciliation=TriggerTableReconciliationService(tables, table_changes),
        update_table_settings=UpdateTableSettingsService(tables, table_changes, clock=clock),
        create_table_maintenance_run=CreateTableMaintenanceRunService(runs, tables),
        get_table_maintenance_run=GetTableMaintenanceRunService(runs),
        list_table_maintenance_runs=ListTableMaintenanceRunsService(runs),
        process_table_maintenance_callback=ProcessTableMaintenanceCallbackService(
            runs, gateways.send_maintenance_result
        ),
        record_table_maintenance_operation_result=RecordTableMaintenanceOperationResultService(runs, tables),
        delete_maintenance_job=DeleteMaintenanceJobService(gateways.delete_maintenance_job),
        get_maintenance_job_status=GetMaintenanceJobStatusService(gateways.read_maintenance_job),
        plan_table_maintenance=PlanTableMaintenanceService(tables, catalog),
        list_table_reconciliations=ListTableReconciliationsService(reconciliations),
        record_table_reconciliation=RecordTableReconciliationService(reconciliations),
        submit_maintenance_operation=SubmitMaintenanceOperationService(runs, tables, gateways.submit_maintenance_job),
    )
