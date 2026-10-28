"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.service.table_discovery_settings.get_table_discovery_settings import (
    GetTableDiscoverySettingsService,
)
from application.service.table.process_table_hint import ProcessTableHintService
from application.service.table.sync_discovered_tables import (
    SyncDiscoveredTablesService,
)
from application.service.table_discovery_settings.update_table_discovery_settings import (
    UpdateTableDiscoverySettingsService,
)
from application.service.table_discovery_rule.create_table_discovery_rule import (
    CreateTableDiscoveryRuleService,
)
from application.service.table_discovery_rule.delete_table_discovery_rule import (
    DeleteTableDiscoveryRuleService,
)
from application.service.table_discovery_rule.list_table_discovery_rules import (
    ListTableDiscoveryRulesService,
)
from application.service.table_discovery_rule.update_table_discovery_rule import (
    UpdateTableDiscoveryRuleService,
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
from application.service.table.exclude_table import (
    ExcludeTableService,
)
from application.service.table.get_table import GetTableService
from application.service.table.include_table import (
    IncludeTableService,
)
from application.service.table.list_tables import (
    ListTablesService,
)
from application.service.table.pause_table import (
    PauseTableService,
)
from application.service.table.reset_table_selection import (
    ResetTableSelectionService,
)
from application.service.table.resume_table import (
    ResumeTableService,
)
from application.service.table.trigger_table_maintenance import (
    TriggerTableMaintenanceService,
)
from application.service.table.update_table_settings import (
    UpdateTableSettingsService,
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
    tables = repos.tables
    rules = repos.table_discovery_rules
    presets = repos.table_maintenance_presets
    runs = repos.maintenance_runs
    discovery = repos.table_discovery_settings
    catalog = gateways.read_table_metadata
    signals = gateways.send_table_signal
    return UseCases(
        get_table_discovery_settings=GetTableDiscoverySettingsService(discovery),
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
        update_table_discovery_settings=UpdateTableDiscoverySettingsService(
            discovery, gateways.update_table_discovery_schedule, clock=clock
        ),
        create_table_discovery_rule=CreateTableDiscoveryRuleService(
            rules, presets, clock=clock
        ),
        delete_table_discovery_rule=DeleteTableDiscoveryRuleService(rules),
        list_table_discovery_rules=ListTableDiscoveryRulesService(rules),
        update_table_discovery_rule=UpdateTableDiscoveryRuleService(
            rules, presets, clock=clock
        ),
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
        exclude_table=ExcludeTableService(tables, catalog, signals, clock=clock),
        get_table=GetTableService(tables),
        include_table=IncludeTableService(
            tables, presets, catalog, signals, clock=clock
        ),
        list_tables=ListTablesService(tables),
        pause_table=PauseTableService(tables, signals, clock=clock),
        reset_table_selection=ResetTableSelectionService(
            tables, rules, presets, signals, clock=clock
        ),
        resume_table=ResumeTableService(tables, signals, clock=clock),
        trigger_table_maintenance=TriggerTableMaintenanceService(tables, signals),
        update_table_settings=UpdateTableSettingsService(tables, signals, clock=clock),
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
