"""Test how planning a table syncs its compaction candidates and compacts only the best of them."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest

from base import validated_copy
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateSelection,
    CandidateState,
    HoldReason,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    SizeMemory,
)
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    CompactionScope,
    CompactionUnit,
    MaintenancePolicyContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.port.inbound.table import PlanTableMaintenanceUseCaseInput
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import TableMetadataObservation
from context.table_maintenance.application.service.table import PlanTableMaintenanceService
from context.table_maintenance.application.service.table_maintenance_policy import (
    UpdateTableMaintenancePolicyService,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

if TYPE_CHECKING:
    from datetime import datetime

KEY = ("iceberg", "sales", "orders")
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
DEFAULT = MaintenancePolicyContent.platform_default()
COMPACTION = MaintenanceOperation.REWRITE_DATA_FILES
RUN = "run-1"
GIB = 1024**3
MIB = 1024**2
LEASE = timedelta(hours=19)
SIZE_MEMORY = {
    ComputeSize.S: SizeMemory(driver_bytes=768 * MIB, executor_bytes=768 * MIB),
    ComputeSize.M: SizeMemory(driver_bytes=GIB, executor_bytes=1536 * MIB),
    ComputeSize.L: SizeMemory(driver_bytes=1536 * MIB, executor_bytes=2 * GIB),
}


def _partition(region: str, files: int, size: int = 10 * 1024, written: datetime | None = None) -> dict[str, Any]:
    return {
        "spec_id": 0,
        "values": [region],
        "data_file_count": files,
        "position_delete_file_count": 0,
        "equality_delete_file_count": 0,
        "total_data_file_size_bytes": size,
        "last_written_at": None if written is None else written.isoformat(),
    }


REGION_SPEC = {
    "spec_id": 0,
    "fields": [
        {
            "field_id": 1000,
            "name": "region",
            "source_column": "region",
            "source_type": "string",
            "transform": "identity",
        }
    ],
}


def _observe(catalog, partitions, specs=None) -> None:  # noqa: ANN001
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = TableMetadataObservation(
        table_uuid="u-1",
        current_snapshot_id=1,
        specs=[REGION_SPEC] if specs is None else specs,
        partitions=partitions,
    )


def _five(catalog) -> None:  # noqa: ANN001
    """Five partitions that qualify (default: at least 5 removable files), a to e from worst to best."""
    _observe(catalog, [_partition(r, files) for r, files in zip("abcde", (6, 7, 8, 9, 10), strict=True)])


def _table(tables_repo, now) -> Table:  # noqa: ANN001
    table = Table.register(TableId("u-1"), NAME, TableDiscoveryRuleId("r-1"), now)
    tables_repo.create(table)
    return table


def _use_policy(policies_repo, now, content) -> None:  # noqa: ANN001
    UpdateTableMaintenancePolicyService(
        policies_repo,
        InMemoryTableMaintenancePolicyAttachmentsRepo(),
        InMemoryTablesRepo(),
        RecordingSendTableChangeGateway(),
        clock=lambda: now,
    ).execute(
        UpdateTableMaintenancePolicyUseCaseInput(name=DEFAULT_POLICY_NAME, content=content.to_primitives(), version=1)
    )


@pytest.fixture
def selection() -> CandidateSelection:
    """Pick two partitions per run, with no filter in the way."""
    return CandidateSelection(partitions_per_run=2)


@pytest.fixture
def planner(tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, selection):  # noqa: ANN001, ANN201
    """Provide the plan service with candidates on the fakes."""
    return PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates_repo,
        runs_repo,
        selection=selection,
        size_memory=SIZE_MEMORY,
        claim_lease=LEASE,
    )


def _plan(planner, now, *, run_id: str | None = RUN, manual=None):  # noqa: ANN001, ANN202
    return planner.execute(
        PlanTableMaintenanceUseCaseInput(table_uuid="u-1", now=now, manual_operations=manual, run_id=run_id)
    )


def _compaction(plan):  # noqa: ANN001, ANN202
    return next((o for o in plan.operations if o.operation == COMPACTION.value), None)


def _check(plan):  # noqa: ANN001, ANN202
    return next(c for c in plan.checks if c.operation == COMPACTION.value)


def _states(candidates_repo) -> dict[str, CandidateState]:  # noqa: ANN001
    return {str(c.partition.values[0]): c.state for c in candidates_repo.list_all()}


def test_plan_takes_only_the_top_n_candidates(planner, tables_repo, catalog, now):
    """Five partitions qualify and two are taken: the plan's filters cover exactly the two best."""
    _table(tables_repo, now)
    _five(catalog)

    compaction = _compaction(_plan(planner, now))

    assert compaction is not None
    (only,) = compaction.filters
    assert "'e'" in only.where
    assert "'d'" in only.where
    assert all(f"'{r}'" not in only.where for r in "abc")
    assert [(p.spec_id, p.values) for p in compaction.candidate_partitions] == [(0, ["e"]), (0, ["d"])]


def test_plan_claims_the_selected_candidates_for_the_run(planner, tables_repo, catalog, candidates_repo, now):
    """The two picked candidates are claimed by the run under a lease; the other three stay pending."""
    _table(tables_repo, now)
    _five(catalog)

    _plan(planner, now)

    assert _states(candidates_repo) == {
        "a": CandidateState.PENDING,
        "b": CandidateState.PENDING,
        "c": CandidateState.PENDING,
        "d": CandidateState.CLAIMED,
        "e": CandidateState.CLAIMED,
    }
    claimed = [c for c in candidates_repo.list_all() if c.state is CandidateState.CLAIMED]
    assert {c.claimed_by_run_id for c in claimed} == {TableMaintenanceRunId(RUN)}
    assert {c.lease_expires_at for c in claimed} == {now + LEASE}


def test_a_retried_plan_keeps_its_own_claims(planner, tables_repo, catalog, candidates_repo, now):
    """Planning again for the same run (a retried plan) plans the partitions it already claimed."""
    _table(tables_repo, now)
    _five(catalog)

    first = _compaction(_plan(planner, now))
    again = _compaction(_plan(planner, now + timedelta(seconds=5)))

    assert again is not None
    assert again.candidate_partitions == first.candidate_partitions
    assert sorted(_states(candidates_repo).values()).count(CandidateState.CLAIMED) == 2


def test_start_size_covers_the_selected_bytes(planner, tables_repo, catalog, now):
    """A table remembered at S that picked 2 GiB of data starts at L."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.S)
    _observe(catalog, [_partition("a", 10, size=GIB), _partition("b", 10, size=GIB)])

    assert _compaction(_plan(planner, now)).start_size == "L"


def test_start_size_keeps_a_larger_remembered_size(planner, tables_repo, catalog, now):
    """A table remembered at M keeps M for a small selection."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.M)
    _five(catalog)

    assert _compaction(_plan(planner, now)).start_size == "M"


def test_dry_run_plan_claims_nothing(planner, tables_repo, catalog, candidates_repo, policies_repo, now):
    """A dry run syncs and scores the candidates but claims none."""
    _use_policy(policies_repo, now, validated_copy(DEFAULT, dry_run=True))
    _table(tables_repo, now)
    _five(catalog)

    plan = _plan(planner, now)

    assert plan.operations == []
    assert set(_states(candidates_repo).values()) == {CandidateState.PENDING}
    assert len(candidates_repo.list_all()) == 5


def test_unpartitioned_table_has_one_whole_table_candidate(planner, tables_repo, catalog, candidates_repo, now):
    """An unpartitioned table has one candidate standing for the whole table, which plans the whole table."""
    _table(tables_repo, now)
    _observe(catalog, [{**_partition("x", 20), "values": []}], specs=[{"spec_id": 0, "fields": []}])

    compaction = _compaction(_plan(planner, now))

    (candidate,) = candidates_repo.list_all()
    assert candidate.partition == PartitionKey.whole_table()
    assert candidate.label == "whole table"
    assert compaction.filters == []
    assert [(p.spec_id, p.values) for p in compaction.candidate_partitions] == [(-1, [])]


def test_whole_table_policy_has_one_whole_table_candidate(
    planner, tables_repo, catalog, candidates_repo, policies_repo, now
):
    """A policy that compacts the whole table has one candidate for it, whatever the partitions."""
    rdf = DEFAULT.operations.rewrite_data_files
    _use_policy(
        policies_repo, now, policy_with_operation(DEFAULT, COMPACTION, scope=CompactionScope(unit=CompactionUnit.TABLE))
    )
    _table(tables_repo, now)
    _five(catalog)
    assert rdf.scope.unit is CompactionUnit.PARTITION

    compaction = _compaction(_plan(planner, now))

    (candidate,) = candidates_repo.list_all()
    assert candidate.partition.is_whole_table
    assert candidate.score.reducible_files == 5 + 6 + 7 + 8 + 9
    assert compaction.filters == []


def test_manual_run_leaves_candidates_alone(planner, tables_repo, catalog, candidates_repo, now):
    """A manual run plans the whole table as before and neither syncs nor claims candidates."""
    _table(tables_repo, now)
    _five(catalog)

    plan = _plan(planner, now, manual=[COMPACTION.value])

    assert candidates_repo.list_all() == []
    assert _compaction(plan).candidate_partitions == []


def test_all_held_plans_no_compaction_and_says_why(
    tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, now
):
    """When every qualifying partition is held, compaction is not planned and the check says all are held."""
    planner = PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates_repo,
        runs_repo,
        selection=CandidateSelection(filters=CandidateFilters(quiet_seconds=120)),
        size_memory=SIZE_MEMORY,
        claim_lease=LEASE,
    )
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10, written=now - timedelta(seconds=30))])

    plan = _plan(planner, now)

    assert _compaction(plan) is None
    check = _check(plan)
    assert check.verdict == "all_held"
    assert check.next_eligible_at == now + timedelta(seconds=90)
    assert plan.next_check_at == now + timedelta(seconds=90)
    assert _states(candidates_repo) == {"a": CandidateState.HELD}
    (held,) = candidates_repo.list_all()
    assert held.hold_reason is HoldReason.RECENTLY_WRITTEN


def test_all_claimed_plans_no_compaction_and_says_why(planner, tables_repo, catalog, candidates_repo, now):
    """When another run still holds every candidate under its lease, compaction is not planned."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan(planner, now, run_id="other-run")

    plan = _plan(planner, now + timedelta(minutes=1))

    assert _compaction(plan) is None
    check = _check(plan)
    assert check.verdict == "all_claimed"
    assert check.next_eligible_at == now + LEASE
    assert _states(candidates_repo) == {"a": CandidateState.CLAIMED}


def test_candidates_of_a_finished_run_are_released(planner, tables_repo, catalog, candidates_repo, runs_repo, now):
    """A claim left by a run that has finished is handed back, so its partitions can be picked again."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan(planner, now, run_id="old-run")
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId("old-run"), TableId("u-1"), TriggerType.SCHEDULED, [COMPACTION], now, execution_ref="wf"
    )
    run.start_attempt(COMPACTION, 1, None, now)
    run.fail(COMPACTION, 1, "boom", now + timedelta(minutes=1))
    runs_repo.create(run)

    plan = _plan(planner, now + timedelta(minutes=2))

    assert _compaction(plan) is not None
    (candidate,) = candidates_repo.list_all()
    assert candidate.claimed_by_run_id == TableMaintenanceRunId(RUN)


def test_healthy_partitions_leave_the_candidates(planner, tables_repo, catalog, candidates_repo, now):
    """A partition that no longer qualifies is removed at the next plan."""
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now, run_id=None)
    _observe(catalog, [_partition("e", 10)])

    _plan(planner, now + timedelta(minutes=1), run_id=None)

    assert list(_states(candidates_repo)) == ["e"]


def test_disabled_compaction_has_no_candidates(planner, tables_repo, catalog, candidates_repo, policies_repo, now):
    """Turning compaction off removes the table's candidates."""
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now, run_id=None)
    _use_policy(policies_repo, now, policy_with_operation(DEFAULT, COMPACTION, enabled=False))

    _plan(planner, now + timedelta(minutes=1))

    assert candidates_repo.list_all() == []


def test_a_dropped_table_loses_its_candidates(planner, tables_repo, catalog, candidates_repo, now):
    """A table skipped as dropped keeps no candidates."""
    table = _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now, run_id=None)
    table.mark_dropped(now)

    assert _plan(planner, now + timedelta(minutes=1)).reason == "dropped"
    assert candidates_repo.list_all() == []


def test_cooling_down_compaction_still_syncs_candidates(planner, tables_repo, catalog, candidates_repo, now):
    """While compaction cools down, candidates are still observed and scored but nothing is claimed."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(minutes=1))
    _five(catalog)

    plan = _plan(planner, now)

    assert _compaction(plan) is None
    assert _check(plan).verdict == "cooling_down"
    assert set(_states(candidates_repo).values()) == {CandidateState.PENDING}


def test_cost_uses_the_remembered_size_and_the_measured_throughput(
    planner, tables_repo, catalog, candidates_repo, runs_repo, now
):
    """The estimate uses the memory of the size compaction starts at and the throughput of past runs."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.M)
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId("past"),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        [COMPACTION],
        now - timedelta(days=1),
        execution_ref="wf",
    )
    run.start_attempt(COMPACTION, 1, None, now - timedelta(days=1))
    run.succeed(COMPACTION, 1, {"rewritten_bytes_count": GIB}, now - timedelta(days=1) + timedelta(hours=1))
    runs_repo.create(run)
    _observe(catalog, [_partition("a", 10, size=GIB)])

    _plan(planner, now, run_id=None)

    (candidate,) = candidates_repo.list_all()
    assert candidate.score.estimated_gb_hours == pytest.approx(2.5)


def test_plan_offers_fewer_partitions_for_an_out_of_memory_retry(
    tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, now
):
    """The compaction carries filter sets: all its partitions, the best half, the best quarter, each once."""
    planner = PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates_repo,
        runs_repo,
        selection=CandidateSelection(partitions_per_run=5),
        size_memory=SIZE_MEMORY,
        claim_lease=LEASE,
    )
    _table(tables_repo, now)
    _five(catalog)

    compaction = _compaction(_plan(planner, now))

    assert compaction.filter_sets[0] == compaction.filters
    wheres = [" ".join(f.where for f in filters) for filters in compaction.filter_sets]
    assert [sum(f"'{r}'" in w for r in "abcde") for w in wheres] == [5, 3, 2]
    assert all(f"'{r}'" in wheres[1] for r in "edc")
    assert all(f"'{r}'" in wheres[2] for r in "ed")


def test_a_single_partition_offers_one_filter_set(planner, tables_repo, catalog, now):
    """With one partition there is nothing fewer to fall back to."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])

    compaction = _compaction(_plan(planner, now))

    assert compaction.filter_sets == [compaction.filters]


def test_whole_table_compaction_offers_no_filter_sets(planner, tables_repo, catalog, now):
    """A whole-table compaction cannot be split, so it carries no filter sets."""
    _table(tables_repo, now)
    _observe(catalog, [{**_partition("x", 20), "values": []}], specs=[{"spec_id": 0, "fields": []}])

    assert _compaction(_plan(planner, now)).filter_sets == []
