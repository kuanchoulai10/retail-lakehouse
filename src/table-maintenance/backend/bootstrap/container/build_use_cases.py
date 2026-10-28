"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.service.discovery.get_discovery_settings import (
    GetDiscoverySettingsService,
)
from application.service.discovery.process_table_hint import ProcessTableHintService
from application.service.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesService,
)
from application.service.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsService,
)
from application.service.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleService,
)
from application.service.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleService,
)
from application.service.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesService,
)
from application.service.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleService,
)
from application.service.maintenance_run.create_maintenance_run import (
    CreateMaintenanceRunService,
)
from application.service.maintenance_run.get_maintenance_run import (
    GetMaintenanceRunService,
)
from application.service.maintenance_run.list_maintenance_runs import (
    ListMaintenanceRunsService,
)
from application.service.maintenance_run.process_maintenance_callback import (
    ProcessMaintenanceCallbackService,
)
from application.service.maintenance_run.record_maintenance_operation_result import (
    RecordMaintenanceOperationResultService,
)
from application.service.managed_table.exclude_managed_table import (
    ExcludeManagedTableService,
)
from application.service.managed_table.get_managed_table import GetManagedTableService
from application.service.managed_table.include_managed_table import (
    IncludeManagedTableService,
)
from application.service.managed_table.list_managed_tables import (
    ListManagedTablesService,
)
from application.service.managed_table.pause_managed_table import (
    PauseManagedTableService,
)
from application.service.managed_table.reset_managed_table_selection import (
    ResetManagedTableSelectionService,
)
from application.service.managed_table.resume_managed_table import (
    ResumeManagedTableService,
)
from application.service.managed_table.trigger_maintenance import (
    TriggerMaintenanceService,
)
from application.service.managed_table.update_managed_table_settings import (
    UpdateManagedTableSettingsService,
)
from application.service.table_maintenance_preset.create_table_maintenance_preset import (
    CreateTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.delete_table_maintenance_preset import (
    DeleteTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.get_table_maintenance_preset import (
    GetTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsService,
)
from application.service.table_maintenance_preset.update_table_maintenance_preset import (
    UpdateTableMaintenancePresetService,
)
from application.service.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobService,
)
from application.service.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusService,
)
from application.service.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceService,
)
from application.service.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationService,
)
from bootstrap.container.use_cases import UseCases

if TYPE_CHECKING:
    from collections.abc import Callable

    from bootstrap.container.gateways import Gateways
    from bootstrap.container.repositories import Repositories


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_use_cases(
    repos: Repositories,
    gateways: Gateways,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> UseCases:
    """Build every application service on the given repositories and gateways."""
    tables = repos.managed_tables
    rules = repos.discovery_rules
    presets = repos.table_maintenance_presets
    runs = repos.maintenance_runs
    discovery = repos.discovery_settings
    catalog = gateways.read_catalog
    signals = gateways.send_table_signal
    return UseCases(
        get_discovery_settings=GetDiscoverySettingsService(discovery),
        process_table_hint=ProcessTableHintService(
            tables,
            rules,
            presets,
            discovery,
            catalog,
            signals,
            gateways.send_discovery_request,
            clock=clock,
        ),
        sync_discovered_tables=SyncDiscoveredTablesService(
            tables, rules, presets, discovery, catalog, signals, clock=clock
        ),
        update_discovery_settings=UpdateDiscoverySettingsService(
            discovery, gateways.update_discovery_schedule, clock=clock
        ),
        create_discovery_rule=CreateDiscoveryRuleService(rules, presets, clock=clock),
        delete_discovery_rule=DeleteDiscoveryRuleService(rules),
        list_discovery_rules=ListDiscoveryRulesService(rules),
        update_discovery_rule=UpdateDiscoveryRuleService(rules, presets, clock=clock),
        create_table_maintenance_preset=CreateTableMaintenancePresetService(
            presets, clock=clock
        ),
        delete_table_maintenance_preset=DeleteTableMaintenancePresetService(
            presets, rules
        ),
        get_table_maintenance_preset=GetTableMaintenancePresetService(presets),
        list_table_maintenance_presets=ListTableMaintenancePresetsService(presets),
        update_table_maintenance_preset=UpdateTableMaintenancePresetService(
            presets, clock=clock
        ),
        exclude_managed_table=ExcludeManagedTableService(
            tables, catalog, signals, clock=clock
        ),
        get_managed_table=GetManagedTableService(tables),
        include_managed_table=IncludeManagedTableService(
            tables, presets, catalog, signals, clock=clock
        ),
        list_managed_tables=ListManagedTablesService(tables),
        pause_managed_table=PauseManagedTableService(tables, signals, clock=clock),
        reset_managed_table_selection=ResetManagedTableSelectionService(
            tables, rules, presets, signals, clock=clock
        ),
        resume_managed_table=ResumeManagedTableService(tables, signals, clock=clock),
        trigger_maintenance=TriggerMaintenanceService(tables, signals),
        update_managed_table_settings=UpdateManagedTableSettingsService(
            tables, signals, clock=clock
        ),
        create_maintenance_run=CreateMaintenanceRunService(runs, tables),
        get_maintenance_run=GetMaintenanceRunService(runs),
        list_maintenance_runs=ListMaintenanceRunsService(runs),
        process_maintenance_callback=ProcessMaintenanceCallbackService(
            runs, gateways.send_maintenance_result
        ),
        record_maintenance_operation_result=RecordMaintenanceOperationResultService(
            runs, tables
        ),
        delete_maintenance_job=DeleteMaintenanceJobService(
            gateways.delete_maintenance_job
        ),
        get_maintenance_job_status=GetMaintenanceJobStatusService(
            gateways.read_maintenance_job
        ),
        plan_table_maintenance=PlanTableMaintenanceService(tables, catalog),
        submit_maintenance_operation=SubmitMaintenanceOperationService(
            runs, tables, gateways.submit_maintenance_job
        ),
    )
