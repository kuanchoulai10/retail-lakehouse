"""Test how planning a table syncs its compaction candidates and compacts only the best of them."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateSelection,
    CandidateState,
    HoldReason,
    PartitionKey,
    StaleCompactionCandidate,
)
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    SizeMemory,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    CompactionScope,
    CompactionUnit,
    MaintenancePolicyContent,
    MaintenancePriority,
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

ROUND_1 = "cr-00000000000000000000000001"

KEY = ("iceberg", "sales", "orders")
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
DEFAULT = MaintenancePolicyContent.platform_default()
COMPACTION = MaintenanceOperation.REWRITE_DATA_FILES
RUN = "mr-00000000000000000000000001"
OTHER_RUN = "mr-00000000000000000000000002"
OLD_RUN = "mr-00000000000000000000000003"
NEVER_STARTED_RUN = "mr-00000000000000000000000004"
NEXT_RUN = "mr-00000000000000000000000005"
PAST_RUN = "mr-00000000000000000000000006"
GIB = 1024**3
MIB = 1024**2
LEASE = timedelta(hours=19)
GRANT_LEASE = timedelta(minutes=10)
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


def _observe_with_manifests(catalog, partitions) -> None:  # noqa: ANN001
    """Observe the partitions on a table whose five small manifests make rewrite_manifests due as well."""
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = TableMetadataObservation(
        table_uuid="u-1",
        current_snapshot_id=1,
        specs=[REGION_SPEC],
        partitions=partitions,
        manifests=[{"length_bytes": 100}] * 5,
    )


def _five(catalog) -> None:  # noqa: ANN001
    """Five partitions that qualify (default: at least 5 removable files), a to e from worst to best."""
    _observe(catalog, [_partition(r, files) for r, files in zip("abcde", (6, 7, 8, 9, 10), strict=True)])


def _table(tables_repo, now) -> Table:  # noqa: ANN001
    table = Table.register(TableId("u-1"), NAME, TableDiscoveryRuleId.new(), now)
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
        PlanTableMaintenanceUseCaseInput(
            table_uuid="u-1", now=now, manual_operations=None if manual is None else tuple(manual), run_id=run_id
        )
    )


def _compaction(plan):  # noqa: ANN001, ANN202
    return next((o for o in plan.operations if o.operation == COMPACTION.value), None)


def _check(plan):  # noqa: ANN001, ANN202
    return next(c for c in plan.checks if c.operation == COMPACTION.value)


def _states(candidates_repo) -> dict[str, CandidateState]:  # noqa: ANN001
    return {str(c.partition.values[0]) if c.partition.values else "": c.state for c in candidates_repo.list_all()}


def _grant(candidates_repo, now, only: str | None = None) -> None:  # noqa: ANN001
    """Grant the table's pending candidates (or the one of partition ``only``) as a compaction round would."""
    pending = [
        c
        for c in candidates_repo.list_unheld()
        if c.state is CandidateState.PENDING and (only is None or c.partition.values == (only,))
    ]
    for candidate in pending:
        candidate.grant(ROUND_1, now + GRANT_LEASE, now)
    candidates_repo.save_all(pending)


def _plan_granted(planner, candidates_repo, now, *, run_id: str | None = RUN):  # noqa: ANN001, ANN202
    """Sync the candidates, let a round grant every pending one, then plan for the run."""
    _plan(planner, now - timedelta(seconds=30), run_id=None)
    _grant(candidates_repo, now - timedelta(seconds=20))
    return _plan(planner, now, run_id=run_id)


def test_plan_takes_only_the_top_n_candidates(planner, tables_repo, catalog, candidates_repo, now):
    """Five partitions are granted and two are taken: the plan's filters cover exactly the two best."""
    _table(tables_repo, now)
    _five(catalog)

    compaction = _compaction(_plan_granted(planner, candidates_repo, now))

    assert compaction is not None
    (only,) = compaction.filters
    assert "'e'" in only.where
    assert "'d'" in only.where
    assert all(f"'{r}'" not in only.where for r in "abc")
    assert [(p.spec_id, p.values) for p in compaction.candidate_partitions] == [(0, ("e",)), (0, ("d",))]


def test_plan_claims_the_selected_candidates_for_the_run(planner, tables_repo, catalog, candidates_repo, now):
    """The two picked candidates are claimed by the run under a lease; the other three stay granted."""
    _table(tables_repo, now)
    _five(catalog)

    _plan_granted(planner, candidates_repo, now)

    assert _states(candidates_repo) == {
        "a": CandidateState.GRANTED,
        "b": CandidateState.GRANTED,
        "c": CandidateState.GRANTED,
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

    first = _compaction(_plan_granted(planner, candidates_repo, now))
    again = _compaction(_plan(planner, now + timedelta(seconds=5)))

    assert again is not None
    assert again.candidate_partitions == first.candidate_partitions
    assert sorted(_states(candidates_repo).values()).count(CandidateState.CLAIMED) == 2


def test_start_size_covers_the_selected_bytes(planner, tables_repo, catalog, candidates_repo, now):
    """A table remembered at S that picked 2 GiB of data starts at L."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.S)
    _observe(catalog, [_partition("a", 10, size=GIB), _partition("b", 10, size=GIB)])

    assert _compaction(_plan_granted(planner, candidates_repo, now)).start_size == "L"


def test_start_size_keeps_a_larger_remembered_size(planner, tables_repo, catalog, candidates_repo, now):
    """A table remembered at M keeps M for a small selection."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.M)
    _five(catalog)

    assert _compaction(_plan_granted(planner, candidates_repo, now)).start_size == "M"


def test_dry_run_plan_claims_nothing(planner, tables_repo, catalog, candidates_repo, policies_repo, now):
    """A dry run syncs and scores the candidates but holds them all not due, so no round grants them."""
    _use_policy(policies_repo, now, DEFAULT.with_changes(dry_run=True))
    _table(tables_repo, now)
    _five(catalog)

    plan = _plan(planner, now)

    assert plan.operations == ()
    assert set(_states(candidates_repo).values()) == {CandidateState.HELD}
    assert {c.hold_reason for c in candidates_repo.list_all()} == {HoldReason.NOT_DUE}
    assert len(candidates_repo.list_all()) == 5


def test_unpartitioned_table_has_one_whole_table_candidate(planner, tables_repo, catalog, candidates_repo, now):
    """An unpartitioned table has one candidate standing for the whole table, which plans the whole table."""
    _table(tables_repo, now)
    _observe(catalog, [{**_partition("x", 20), "values": []}], specs=[{"spec_id": 0, "fields": []}])

    compaction = _compaction(_plan_granted(planner, candidates_repo, now))

    (candidate,) = candidates_repo.list_all()
    assert candidate.partition == PartitionKey.whole_table()
    assert candidate.label == "whole table"
    assert compaction.filters == ()
    assert [(p.spec_id, p.values) for p in compaction.candidate_partitions] == [(-1, ())]


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

    compaction = _compaction(_plan_granted(planner, candidates_repo, now))

    (candidate,) = candidates_repo.list_all()
    assert candidate.partition.is_whole_table
    assert candidate.score.reducible_files == 5 + 6 + 7 + 8 + 9
    assert compaction.filters == ()


def test_manual_run_leaves_candidates_alone(planner, tables_repo, catalog, candidates_repo, now):
    """A manual run plans the whole table as before and neither syncs nor claims candidates."""
    _table(tables_repo, now)
    _five(catalog)

    plan = _plan(planner, now, manual=[COMPACTION.value])

    assert candidates_repo.list_all() == []
    assert _compaction(plan).candidate_partitions == ()


def test_manual_run_leaves_grants_alone(planner, tables_repo, catalog, candidates_repo, now):
    """A manual run compacts the whole table and leaves granted candidates granted for the next scheduled plan."""
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now - timedelta(seconds=30), run_id=None)
    _grant(candidates_repo, now - timedelta(seconds=20))

    plan = _plan(planner, now, manual=[COMPACTION.value], run_id="manual-run")

    assert _compaction(plan).candidate_partitions == ()
    assert set(_states(candidates_repo).values()) == {CandidateState.GRANTED}


def test_due_compaction_without_a_grant_starts_nothing_and_says_awaiting_schedule(
    planner, tables_repo, catalog, candidates_repo, now
):
    """A due compaction waits for a compaction round; the other due operations are still planned."""
    _table(tables_repo, now)
    _observe_with_manifests(catalog, [_partition(r, files) for r, files in zip("abcde", (6, 7, 8, 9, 10), strict=True)])

    plan = _plan(planner, now)

    assert _compaction(plan) is None
    assert "rewrite_manifests" in [o.operation for o in plan.operations]
    check = _check(plan)
    assert check.verdict == "awaiting_schedule"
    assert check.next_eligible_at is None
    assert plan.next_check_at is None
    assert set(_states(candidates_repo).values()) == {CandidateState.PENDING}


def test_due_compaction_claims_its_granted_candidates_only(planner, tables_repo, catalog, candidates_repo, now):
    """Granted d and e are claimed and named in the run's filter; pending c is left for a later round."""
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now - timedelta(seconds=30), run_id=None)
    _grant(candidates_repo, now - timedelta(seconds=20), only="e")
    _grant(candidates_repo, now - timedelta(seconds=20), only="c")

    compaction = _compaction(_plan(planner, now))

    assert compaction is not None
    (only,) = compaction.filters
    assert "'e'" in only.where
    assert "'c'" in only.where
    assert "'d'" not in only.where
    states = _states(candidates_repo)
    assert (states["c"], states["e"], states["d"]) == (
        CandidateState.CLAIMED,
        CandidateState.CLAIMED,
        CandidateState.PENDING,
    )
    claimed = [c for c in candidates_repo.list_all() if c.state is CandidateState.CLAIMED]
    assert {c.granted_round_id for c in claimed} == {ROUND_1}


def test_cooling_down_compaction_holds_candidates_in_cooldown(
    tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, now
):
    """While compaction cools down its candidates are held in cooldown; a too-small one still says too small."""
    planner = PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates_repo,
        runs_repo,
        selection=CandidateSelection(filters=CandidateFilters(min_partition_bytes=1000)),
        size_memory=SIZE_MEMORY,
        claim_lease=LEASE,
    )
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(minutes=1))
    _observe(catalog, [_partition("a", 10, size=10_000), _partition("b", 10, size=10)])

    plan = _plan(planner, now)

    assert _check(plan).verdict == "cooling_down"
    reasons = {str(c.partition.values[0]): c.hold_reason for c in candidates_repo.list_all()}
    assert reasons == {"a": HoldReason.COOLDOWN, "b": HoldReason.TOO_SMALL}


def test_failure_backoff_cap_bounds_how_long_compaction_cools_down(
    tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, now
):
    """A compaction that keeps failing cools down only up to the configured cap, then is planned again."""
    planner = PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates_repo,
        runs_repo,
        selection=CandidateSelection(),
        size_memory=SIZE_MEMORY,
        claim_lease=LEASE,
        failure_backoff_cap=timedelta(hours=3),
    )
    table = _table(tables_repo, now)
    for _ in range(10):
        table.record_operation_result(COMPACTION, False, now - timedelta(hours=4))
    _observe(catalog, [_partition("a", 10)])

    plan = _plan(planner, now)

    assert _check(plan).verdict != "cooling_down"


def test_candidates_take_the_policy_priority(planner, tables_repo, catalog, candidates_repo, policies_repo, now):
    """The candidates carry the priority of the policy that applies to the table."""
    _use_policy(policies_repo, now, DEFAULT.with_changes(priority=MaintenancePriority.P0))
    _table(tables_repo, now)
    _five(catalog)

    _plan(planner, now)

    assert {c.priority for c in candidates_repo.list_all()} == {MaintenancePriority.P0}


def test_a_stale_save_raises_for_the_activity_to_retry(planner, tables_repo, catalog, candidates_repo, now):
    """When a round grants a candidate between the plan's read and its save, the plan raises and saves nothing."""
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now - timedelta(minutes=1), run_id=None)
    read = candidates_repo.list_by_table

    def read_then_a_round_grants(table_uuid):  # noqa: ANN001, ANN202
        candidates = read(table_uuid)
        _grant(candidates_repo, now - timedelta(seconds=1), only="e")
        return candidates

    candidates_repo.list_by_table = read_then_a_round_grants

    with pytest.raises(StaleCompactionCandidate):
        _plan(planner, now)

    candidates_repo.list_by_table = read
    assert _states(candidates_repo)["e"] is CandidateState.GRANTED
    assert {s for v, s in _states(candidates_repo).items() if v != "e"} == {CandidateState.PENDING}


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


def _run_record(runs_repo, run_id: str, now, *, finished: bool) -> None:  # noqa: ANN001
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(run_id), TableId("u-1"), TriggerType.SCHEDULED, [COMPACTION], now, execution_ref="wf"
    )
    run.start_attempt(COMPACTION, 1, None, now)
    if finished:
        run.fail(COMPACTION, 1, "boom", now + timedelta(minutes=1))
    runs_repo.create(run)


def test_all_claimed_plans_no_compaction_and_says_why(planner, tables_repo, catalog, candidates_repo, runs_repo, now):
    """When another run still holds every candidate under its lease, compaction is not planned."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan_granted(planner, candidates_repo, now, run_id=OTHER_RUN)
    _run_record(runs_repo, OTHER_RUN, now, finished=False)

    plan = _plan(planner, now + timedelta(minutes=1))

    assert _compaction(plan) is None
    check = _check(plan)
    assert check.verdict == "all_claimed"
    assert check.next_eligible_at == now + LEASE
    assert _states(candidates_repo) == {"a": CandidateState.CLAIMED}


def test_candidates_of_a_finished_run_are_released(planner, tables_repo, catalog, candidates_repo, runs_repo, now):
    """A claim left by a run that has finished is handed back to the next round, then can be taken again."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan_granted(planner, candidates_repo, now, run_id=OLD_RUN)
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(OLD_RUN), TableId("u-1"), TriggerType.SCHEDULED, [COMPACTION], now, execution_ref="wf"
    )
    run.start_attempt(COMPACTION, 1, None, now)
    run.fail(COMPACTION, 1, "boom", now + timedelta(minutes=1))
    runs_repo.create(run)

    released = _plan(planner, now + timedelta(minutes=2))
    assert _check(released).verdict == "awaiting_schedule"
    assert _states(candidates_repo) == {"a": CandidateState.PENDING}
    _grant(candidates_repo, now + timedelta(minutes=3))
    plan = _plan(planner, now + timedelta(minutes=4))

    assert _compaction(plan) is not None
    (candidate,) = candidates_repo.list_all()
    assert candidate.claimed_by_run_id == TableMaintenanceRunId(RUN)


def test_plan_releases_claims_of_a_run_that_never_started(planner, tables_repo, catalog, candidates_repo, now):
    """A plan that saved its claims and then failed leaves a run id with no run record: its claims are freed.

    The reconciliation plans only when no run of the table is in flight, so a
    claim of a run that has no record belongs to a plan whose run never started.
    """
    _table(tables_repo, now)
    _five(catalog)
    _plan(planner, now - timedelta(seconds=30), run_id=None)
    _grant(candidates_repo, now - timedelta(seconds=20), only="d")
    _grant(candidates_repo, now - timedelta(seconds=20), only="e")
    _plan(planner, now, run_id=NEVER_STARTED_RUN)

    released = _plan(planner, now + timedelta(minutes=5), run_id=NEXT_RUN)
    assert _check(released).verdict == "awaiting_schedule"
    _grant(candidates_repo, now + timedelta(minutes=6))
    plan = _plan(planner, now + timedelta(minutes=7), run_id=NEXT_RUN)

    compaction = _compaction(plan)
    assert compaction is not None
    assert [(p.spec_id, p.values) for p in compaction.candidate_partitions] == [(0, ("e",)), (0, ("d",))]
    claimed = [c for c in candidates_repo.list_all() if c.state is CandidateState.CLAIMED]
    assert {c.claimed_by_run_id for c in claimed} == {TableMaintenanceRunId(NEXT_RUN)}


def test_claims_of_a_finished_run_older_than_the_recent_runs_are_released(
    planner, tables_repo, catalog, candidates_repo, runs_repo, now
):
    """The release looks each holder up, so a finished run past the newest runs read for throughput still counts."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan_granted(planner, candidates_repo, now, run_id=OLD_RUN)
    _run_record(runs_repo, OLD_RUN, now, finished=True)
    for i in range(60):
        _run_record(runs_repo, TableMaintenanceRunId.new().value, now + timedelta(minutes=2 + i), finished=True)

    _plan(planner, now + timedelta(hours=2), run_id=None)
    _grant(candidates_repo, now + timedelta(hours=2, minutes=1))
    plan = _plan(planner, now + timedelta(hours=2, minutes=2))

    assert _compaction(plan) is not None
    (candidate,) = candidates_repo.list_all()
    assert candidate.claimed_by_run_id == TableMaintenanceRunId(RUN)


def test_reobserved_partition_keeps_its_candidate_id(planner, tables_repo, catalog, candidates_repo, now):
    """A partition observed again updates its stored candidate: one row, the same id, the new observation."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("e", 10)])
    _plan(planner, now, run_id=None)
    (first,) = candidates_repo.list_all()
    _observe(catalog, [_partition("e", 12)])

    _plan(planner, now + timedelta(minutes=1), run_id=None)

    (again,) = candidates_repo.list_all()
    assert again.id == first.id
    assert again.score.reducible_files > first.score.reducible_files
    assert again.version == first.version + 1


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
    """While compaction cools down, candidates are still observed and scored, held not due, and nothing is claimed."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(minutes=1))
    _five(catalog)

    plan = _plan(planner, now)

    assert _compaction(plan) is None
    assert _check(plan).verdict == "cooling_down"
    assert set(_states(candidates_repo).values()) == {CandidateState.HELD}


def test_cost_uses_the_remembered_size_and_the_measured_throughput(
    planner, tables_repo, catalog, candidates_repo, runs_repo, now
):
    """The estimate uses the memory of the size compaction starts at and the throughput of past runs."""
    table = _table(tables_repo, now)
    table.record_operation_result(COMPACTION, True, now - timedelta(days=1), size=ComputeSize.M)
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(PAST_RUN),
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


def test_cost_ignores_past_compactions_below_the_throughput_floor(
    planner, tables_repo, catalog, candidates_repo, runs_repo, now
):
    """A past compaction of a few MiB measures Spark start-up, not throughput: the default is used instead."""
    _table(tables_repo, now)
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId(PAST_RUN),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        [COMPACTION],
        now - timedelta(days=1),
        execution_ref="wf",
    )
    run.start_attempt(COMPACTION, 1, None, now - timedelta(days=1))
    run.succeed(COMPACTION, 1, {"rewritten_bytes_count": MIB}, now - timedelta(days=1) + timedelta(minutes=3))
    runs_repo.create(run)
    _observe(catalog, [_partition("a", 10, size=GIB)])

    _plan(planner, now, run_id=None)

    (candidate,) = candidates_repo.list_all()
    assert candidate.score.estimated_gb_hours == pytest.approx(1.5 * GIB / (2.0 * GIB))


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

    compaction = _compaction(_plan_granted(planner, candidates_repo, now))

    assert compaction.filter_sets[0] == compaction.filters
    wheres = [" ".join(f.where for f in filters) for filters in compaction.filter_sets]
    assert [sum(f"'{r}'" in w for r in "abcde") for w in wheres] == [5, 3, 2]
    assert all(f"'{r}'" in wheres[1] for r in "edc")
    assert all(f"'{r}'" in wheres[2] for r in "ed")


def test_a_single_partition_offers_one_filter_set(planner, tables_repo, catalog, candidates_repo, now):
    """With one partition there is nothing fewer to fall back to."""
    _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])

    compaction = _compaction(_plan_granted(planner, candidates_repo, now))

    assert compaction.filter_sets == (compaction.filters,)


def test_whole_table_compaction_offers_no_filter_sets(planner, tables_repo, catalog, candidates_repo, now):
    """A whole-table compaction cannot be split, so it carries no filter sets."""
    _table(tables_repo, now)
    _observe(catalog, [{**_partition("x", 20), "values": []}], specs=[{"spec_id": 0, "fields": []}])

    assert _compaction(_plan_granted(planner, candidates_repo, now)).filter_sets == ()


def test_a_granted_partition_written_since_is_held_not_claimed(
    tables_repo, catalog, resolve_applicable_policy, candidates_repo, runs_repo, now
):
    """A write after the grant holds the partition as recently written; the plan does not compact it."""
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
    _observe(catalog, [_partition("a", 10, written=now - timedelta(hours=1))])
    _plan(planner, now - timedelta(seconds=30), run_id=None)
    _grant(candidates_repo, now - timedelta(seconds=20))
    _observe(catalog, [_partition("a", 11, written=now - timedelta(seconds=5))])

    plan = _plan(planner, now)

    assert _compaction(plan) is None
    (held,) = candidates_repo.list_all()
    assert (held.state, held.hold_reason, held.granted_round_id) == (
        CandidateState.HELD,
        HoldReason.RECENTLY_WRITTEN,
        None,
    )


def test_a_cooldown_keeps_the_wait_and_a_dry_run_ends_it(
    planner, tables_repo, catalog, candidates_repo, policies_repo, now
):
    """Only the cooldown keeps a pending candidate's wait for a round; a dry run is not waiting for one."""
    table = _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    _plan(planner, now, run_id=None)
    (pending,) = candidates_repo.list_all()
    assert pending.pending_since == now
    table.record_operation_result(COMPACTION, True, now + timedelta(minutes=1))

    _plan(planner, now + timedelta(minutes=2), run_id=None)
    (cooling,) = candidates_repo.list_all()
    assert (cooling.hold_reason, cooling.pending_since) == (HoldReason.COOLDOWN, now)

    _use_policy(policies_repo, now, DEFAULT.with_changes(dry_run=True))
    _plan(planner, now + timedelta(minutes=3), run_id=None)
    (dry,) = candidates_repo.list_all()
    assert (dry.hold_reason, dry.pending_since) == (HoldReason.NOT_DUE, None)


def test_a_table_needing_attention_ends_the_wait(planner, tables_repo, catalog, candidates_repo, now):
    """Compaction marked as needing attention is not waiting for a round, even within its cooldown."""
    table = _table(tables_repo, now)
    _observe(catalog, [_partition("a", 10)])
    first = _plan(planner, now, run_id=None)
    applied = AppliedPolicyRef(name=first.policy_name, version=first.policy_version, target=first.policy_target)
    table.record_operation_result(COMPACTION, True, now + timedelta(minutes=1))
    mark = AttentionMark(since=now + timedelta(minutes=1), reason="out of memory at size L", policy=applied)
    table.mark_needs_attention(COMPACTION, mark, now + timedelta(minutes=1))

    _plan(planner, now + timedelta(minutes=2), run_id=None)

    (held,) = candidates_repo.list_all()
    assert (held.hold_reason, held.pending_since) == (HoldReason.NOT_DUE, None)
