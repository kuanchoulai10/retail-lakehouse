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
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.service.compaction_candidate import ListCompactionCandidatesService

TABLE = TableId("u-1")
RUN = TableMaintenanceRunId("run-1")


def _candidate(value: str, score: float, now, *, hold: HoldReason | None = None, files: int = 10):  # noqa: ANN001, ANN202
    return CompactionCandidate.create(
        table_uuid=TABLE,
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=files, data_bytes=2048, estimated_gb_hours=0.25, score=score),
        last_written_at=now - timedelta(hours=1),
        hold_reason=hold,
        now=now,
    )


@pytest.fixture
def service(candidates_repo, tables_repo, now):  # noqa: ANN001, ANN201
    """Provide the service over a known table with four candidates."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId("r"), now
        )
    )
    claimed = _candidate("2026-11-04", 0.9, now)
    claimed.grant("round-1", now + timedelta(minutes=10), now)
    claimed.claim(RUN, now + timedelta(hours=1), now)
    candidates_repo.save_all(
        [
            _candidate("2026-11-01", 0.4, now),
            _candidate("2026-11-02", 0.8, now, hold=HoldReason.RECENTLY_WRITTEN),
            _candidate("2026-11-03", 0.6, now),
            claimed,
        ]
    )
    return ListCompactionCandidatesService(candidates_repo, tables_repo, partitions_per_run=2)


def test_candidates_come_best_first_and_only_pending_ones_are_ranked(service):
    """The list is sorted by score; ranks count the pending candidates only."""
    out = service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1"))

    assert out.partitions_per_run == 2
    assert [(i.values, i.state, i.rank) for i in out.items] == [
        (["2026-11-04"], "claimed", None),
        (["2026-11-02"], "held", None),
        (["2026-11-03"], "pending", 1),
        (["2026-11-01"], "pending", 2),
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


def test_a_table_without_candidates_lists_none(candidates_repo, tables_repo, now):
    """A known table with nothing to compact has an empty list."""
    tables_repo.create(
        Table.register(
            TABLE, TableName(catalog="iceberg", namespace="sales", table="orders"), TableDiscoveryRuleId("r"), now
        )
    )
    service = ListCompactionCandidatesService(candidates_repo, tables_repo, partitions_per_run=10)

    assert service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="u-1")).items == []


def test_an_unknown_table_is_not_found(candidates_repo, tables_repo):
    """Listing the candidates of a table maintenance does not know is a not-found error."""
    service = ListCompactionCandidatesService(candidates_repo, tables_repo, partitions_per_run=10)

    with pytest.raises(NotFoundError):
        service.execute(ListCompactionCandidatesUseCaseInput(table_uuid="nope"))
