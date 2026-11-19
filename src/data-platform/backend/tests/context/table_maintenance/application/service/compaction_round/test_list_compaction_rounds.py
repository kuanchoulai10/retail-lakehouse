"""Test listing the recorded compaction rounds."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.port.inbound.compaction_round import (
    ListCompactionRoundsUseCaseInput,
    ListCompactionRoundsUseCaseOutput,
)
from context.table_maintenance.application.service.compaction_round import ListCompactionRoundsService
from tests.context.table_maintenance.application.service.compaction_round.recorded_round import recorded_round
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def _service(tables_repo):  # noqa: ANN001, ANN202
    tables_repo.create(
        Table.register(
            TableId("t-1"),
            TableName(catalog="ice.berg", namespace="sales.eu", table="orders"),
            TableDiscoveryRuleId.new(),
            NOW,
        )
    )
    rounds = InMemoryCompactionRoundsRepo()
    for minutes in (0, 2, 4):
        rounds.save(recorded_round(f"round-{minutes}", NOW + timedelta(minutes=minutes)))
    return ListCompactionRoundsService(rounds, tables_repo)


def test_rounds_come_newest_first_up_to_the_limit(tables_repo):
    """The newest rounds are listed first, at most ``limit`` of them."""
    out = _service(tables_repo).execute(ListCompactionRoundsUseCaseInput(limit=2))

    assert [r.round_id for r in out.items] == ["round-4", "round-2"]


def test_before_pages_to_older_rounds(tables_repo):
    """``before`` lists only rounds that started before it, so the last round's start fetches the next page."""
    out = _service(tables_repo).execute(ListCompactionRoundsUseCaseInput(limit=2, before=NOW + timedelta(minutes=2)))

    assert [r.round_id for r in out.items] == ["round-0"]


def test_a_round_carries_its_budget_picks_and_skips_with_table_names(tables_repo):
    """Each round says its budget and use, its picks and skips; a table no longer known has no name."""
    item = _service(tables_repo).execute(ListCompactionRoundsUseCaseInput(limit=1)).items[0]

    assert item == ListCompactionRoundsUseCaseOutput.CompactionRound(
        round_id="round-4",
        started_at=NOW + timedelta(minutes=4),
        budget_gb_hours=0.05,
        used_gb_hours=0.04,
        picks=(
            ListCompactionRoundsUseCaseOutput.Pick(
                table_uuid="t-1",
                table_name="ice.berg.sales.eu.orders",
                spec_id=0,
                values=("2026-11-01",),
                partition_label="day=2026-11-01",
                priority="P0",
                score=0.5,
                weighted_score=2.0,
                estimated_gb_hours=0.04,
                overdue=True,
                catalog="ice.berg",
                namespace=("sales", "eu"),
                table="orders",
            ),
        ),
        skips=(
            ListCompactionRoundsUseCaseOutput.Skip(
                table_uuid="t-2",
                table_name=None,
                spec_id=-1,
                values=(),
                partition_label="whole table",
                priority="P2",
                score=0.6,
                weighted_score=0.6,
                estimated_gb_hours=0.03,
                overdue=False,
                reason="budget_used",
            ),
        ),
        skipped_total=3,
        busy_skipped=4,
    )
