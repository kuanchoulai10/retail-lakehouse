"""Provide the build_use_cases function."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from bootstrap.configs import SchedulerSettings
from bootstrap.container.build_priority_sla import build_priority_sla
from bootstrap.container.build_priority_weights import build_priority_weights
from bootstrap.container.use_cases import UseCases
from context.table_maintenance.application.domain.model.compaction_candidate import CandidateSelection
from context.table_maintenance.application.domain.model.table import DEFAULT_FAILURE_BACKOFF_CAP
from context.table_maintenance.application.service.compaction_candidate import (
    ListCompactionCandidatesService,
    ReleaseCompactionCandidatesService,
)
from context.table_maintenance.application.service.compaction_round import (
    GetCompactionRoundService,
    GetSchedulerSettingsService,
    ListCompactionRoundsService,
    ScheduleCompactionRoundService,
)
from context.table_maintenance.application.service.table import (
    GetTableHealthService,
    GetTableService,
    GetTableStorageService,
    ListTableCommitsService,
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


_DEFAULT_CLAIM_LEASE = timedelta(hours=20)


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
    candidate_selection: CandidateSelection | None = None,
    claim_lease: timedelta = _DEFAULT_CLAIM_LEASE,
    scheduler: SchedulerSettings | None = None,
    failure_backoff_cap: timedelta = DEFAULT_FAILURE_BACKOFF_CAP,
) -> UseCases:
    """Build every application service on the given repositories and gateways.

    ``size_memory`` is the memory each compute size runs with; without it no
    operation is ever stepped down to a smaller size, and compaction costs are
    estimated for a fixed memory. ``candidate_selection`` says how compaction
    candidates are picked (the defaults without it) and ``claim_lease`` how long
    a run holds the candidates it claims. ``scheduler`` says how compaction
    rounds share compaction across tables (the defaults without it).
    ``failure_backoff_cap`` is where the doubling of a failing operation's
    cooldown stops. ``platform_settings`` are the values the platform settings
    page lists; every caller gives them, so none shows defaults by accident.
    """
    tables = repos.tables
    rules = repos.table_discovery_rules
    policies = repos.table_maintenance_policies
    attachments = repos.table_maintenance_policy_attachments
    runs = repos.table_maintenance_runs
    reconciliations = repos.table_reconciliations
    candidates = repos.compaction_candidates
    discoveries = repos.catalog_discoveries
    selection = candidate_selection or CandidateSelection()
    rounds = scheduler or SchedulerSettings()
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
        get_table_health=GetTableHealthService(
            tables, catalog, resolve_applicable_policy, failure_backoff_cap=failure_backoff_cap, clock=clock
        ),
        get_table_storage=GetTableStorageService(tables, catalog, runs, clock=clock),
        list_table_commits=ListTableCommitsService(tables, catalog),
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
            candidates_repo=candidates,
        ),
        delete_maintenance_job=DeleteMaintenanceJobService(gateways.delete_maintenance_job),
        get_maintenance_job_status=GetMaintenanceJobStatusService(gateways.read_maintenance_job),
        get_maintenance_job_pods=GetMaintenanceJobPodsService(gateways.read_maintenance_job_pods),
        plan_table_maintenance=PlanTableMaintenanceService(
            tables,
            catalog,
            resolve_applicable_policy,
            candidates,
            runs,
            selection=selection,
            size_memory=size_memory or {},
            claim_lease=claim_lease,
            failure_backoff_cap=failure_backoff_cap,
        ),
        release_compaction_candidates=ReleaseCompactionCandidatesService(candidates),
        schedule_compaction_round=ScheduleCompactionRoundService(
            candidates,
            repos.compaction_rounds,
            tables,
            weights=build_priority_weights(rounds),
            budget_gb_hours=rounds.budget_gb_hours,
            partitions_per_run=selection.partitions_per_run,
            sla=build_priority_sla(rounds),
            grant_lease=timedelta(seconds=rounds.grant_lease_seconds),
            rounds_kept=rounds.rounds_kept,
        ),
        list_compaction_rounds=ListCompactionRoundsService(repos.compaction_rounds, tables),
        get_compaction_round=GetCompactionRoundService(repos.compaction_rounds, tables),
        get_scheduler_settings=GetSchedulerSettingsService(
            weights=build_priority_weights(rounds),
            sla=build_priority_sla(rounds),
            round_seconds=rounds.round_seconds,
            budget_gb_hours=rounds.budget_gb_hours,
            grant_lease=timedelta(seconds=rounds.grant_lease_seconds),
        ),
        get_platform_settings=GetPlatformSettingsService(platform_settings),
        list_compaction_candidates=ListCompactionCandidatesService(
            candidates,
            tables,
            repos.compaction_rounds,
            partitions_per_run=selection.partitions_per_run,
            sla=build_priority_sla(rounds),
            clock=clock,
        ),
        list_table_reconciliations=ListTableReconciliationsService(reconciliations, policies),
        record_table_reconciliation=RecordTableReconciliationService(reconciliations),
        submit_maintenance_operation=SubmitMaintenanceOperationService(
            runs, tables, gateways.submit_maintenance_job, candidates_repo=candidates
        ),
    )
