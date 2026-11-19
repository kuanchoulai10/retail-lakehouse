"""Test listing the compaction candidates of a table."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CompactionCandidate,
    HoldReason,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.service.compaction_candidate import ListCompactionCandidatesService
from tests.context.table_maintenance.application.service.compaction_round.recorded_round import recorded_round
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo

TABLE = TableId("u-1")
RUN = TableMaintenanceRunId("run-1")
SLA = {
    MaintenancePriority.P0: timedelta(hours=1),
    MaintenancePriority.P1: timedelta(hours=4),
    MaintenancePriority.P2: timedelta(hours=8),
}


def _candidate(  # noqa: ANN202
    value: str,
    score: float,
    now,  # noqa: ANN001
    *,
    hold: HoldReason | None = None,
    files: int = 10,
    priority: MaintenancePriority = MaintenancePriority.P2,
):
    return CompactionCandidate.create(
        table_uuid=TABLE,
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=files, data_bytes=2048, estimated_gb_hours=0.25, score=score),
        last_written_at=now - timedelta(hours=1),
        hold_reason=hold,
        now=now,
        priority=priority,
    )


@pytest.fixture
def service(candidates_repo, tables_repo, now):  # noqa: ANN001, ANN201
    """Provide the service over a known table with four candidates."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId.new(), now
        )
    )
    claimed = _candidate("2026-11-04", 0.9, now)
    claimed.grant("round-1", now + timedelta(minutes=10), now)
    claimed.claim(RUN, now + timedelta(hours=1), now)
    candidates_repo.save_all(
        [
            _candidate("2026-11-01", 0.4, now),
            _candidate("2026-11-02", 0.8, now, hold=HoldReason.RECENTLY_WRITTEN),
            _candidate("2026-11-03", 0.6, now, priority=MaintenancePriority.P0),
            claimed,
        ]
    )
    return ListCompactionCandidatesService(
        candidates_repo,
        tables_repo,
        InMemoryCompactionRoundsRepo(),
        partitions_per_run=2,
        sla=SLA,
        clock=lambda: now + timedelta(hours=2),
    )


def test_candidates_come_best_first_and_only_pending_ones_are_ranked(service):
    """The list is sorted by score; ranks count the pending candidates only."""
    out = service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1"))

    assert out.partitions_per_run == 2
    assert [(i.values, i.state, i.rank) for i in out.items] == [
        (("2026-11-04",), "claimed", None),
        (("2026-11-02",), "held", None),
        (("2026-11-03",), "pending", 1),
        (("2026-11-01",), "pending", 2),
    ]


def test_each_candidate_says_what_it_is_worth_and_who_holds_it(service, now):
    """An item carries the partition, its label, the score parts, the hold and the claim."""
    items = service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1")).items

    claimed, held = items[0], items[1]
    assert (claimed.spec_id, claimed.partition_label) == (0, "day=2026-11-04")
    assert (claimed.reducible_files, claimed.data_bytes, claimed.estimated_gb_hours, claimed.score) == (
        10,
        2048,
        0.25,
        0.9,
    )
    assert (claimed.claimed_by_run_id, claimed.lease_expires_at) == ("run-1", now + timedelta(hours=1))
    assert (held.hold_reason, held.claimed_by_run_id) == ("recently_written", None)
    assert held.last_written_at == now - timedelta(hours=1)
    assert held.observed_at == now


def test_each_candidate_says_its_priority_grant_and_whether_it_is_overdue(service, candidates_repo, now):
    """An item carries the priority, the round that granted it, its wait start and the overdue mark of its SLA."""
    granted = next(c for c in candidates_repo.list_by_table(TABLE) if c.partition.values == ("2026-11-01",))
    granted.grant("round-7", now + timedelta(hours=3), now)
    candidates_repo.save_all([granted])

    items = {i.values[0]: i for i in service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1")).items}

    p0, p2 = items["2026-11-03"], items["2026-11-01"]
    assert (p0.priority, p0.granted_round_id, p0.pending_since, p0.overdue) == ("P0", None, now, True)
    assert (p2.priority, p2.state, p2.granted_round_id, p2.overdue) == ("P2", "granted", "round-7", False)
    assert (items["2026-11-04"].pending_since, items["2026-11-04"].overdue) == (None, False)
    assert (items["2026-11-02"].granted_round_id, items["2026-11-02"].overdue) == (None, False)


def test_a_table_without_candidates_lists_none(candidates_repo, tables_repo, now):
    """A known table with nothing to compact has an empty list."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId.new(), now
        )
    )
    service = ListCompactionCandidatesService(
        candidates_repo, tables_repo, InMemoryCompactionRoundsRepo(), partitions_per_run=10, sla=SLA
    )

    assert service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1")).items == ()


def test_an_unknown_table_is_not_found(candidates_repo, tables_repo):
    """Listing the candidates of a table maintenance does not know is a not-found error."""
    service = ListCompactionCandidatesService(
        candidates_repo, tables_repo, InMemoryCompactionRoundsRepo(), partitions_per_run=10, sla=SLA
    )

    with pytest.raises(NotFoundError):
        service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="nope"))


def test_a_grant_whose_lease_ended_reads_as_pending(candidates_repo, tables_repo, now):  # noqa: ANN001
    """A grant nobody claimed in time is shown as pending again, ranked, without its round, until it is observed."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId.new(), now
        )
    )
    expired, live = _candidate("2026-11-01", 0.9, now), _candidate("2026-11-02", 0.5, now)
    expired.grant("round-1", now + timedelta(minutes=10), now)
    live.grant("round-2", now + timedelta(hours=1), now)
    candidates_repo.save_all([expired, live, _candidate("2026-11-03", 0.4, now)])
    service = ListCompactionCandidatesService(
        candidates_repo,
        tables_repo,
        InMemoryCompactionRoundsRepo(),
        partitions_per_run=2,
        sla=SLA,
        clock=lambda: now + timedelta(minutes=30),
    )

    items = service.execute(ListCompactionCandidatesUseCaseInput(table_uuid=TABLE.value)).items

    assert [(i.state, i.granted_round_id, i.lease_expires_at is None, i.rank) for i in items] == [
        ("pending", None, True, 1),
        ("granted", "round-2", False, None),
        ("pending", None, True, 2),
    ]


def test_a_granted_candidate_says_when_its_round_started(candidates_repo, tables_repo, now):  # noqa: ANN001
    """A grant names its round by the round's start, so people find it in the rounds list; a purged round has none."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId.new(), now
        )
    )
    rounds = InMemoryCompactionRoundsRepo()
    rounds.save(recorded_round("compaction-rounds-1", now - timedelta(seconds=30)))
    kept, purged = _candidate("2026-11-01", 0.9, now), _candidate("2026-11-02", 0.5, now)
    kept.grant("compaction-rounds-1", now + timedelta(minutes=10), now)
    purged.grant("compaction-rounds-0", now + timedelta(minutes=10), now)
    candidates_repo.save_all([kept, purged, _candidate("2026-11-03", 0.4, now)])
    service = ListCompactionCandidatesService(
        candidates_repo, tables_repo, rounds, partitions_per_run=2, sla=SLA, clock=lambda: now
    )

    items = service.execute(ListCompactionCandidatesUseCaseInput(table_uuid=TABLE.value)).items

    assert [i.granted_round_started_at for i in items] == [now - timedelta(seconds=30), None, None]
