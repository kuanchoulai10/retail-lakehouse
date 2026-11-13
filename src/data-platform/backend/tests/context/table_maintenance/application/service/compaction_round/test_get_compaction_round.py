"""Test reading one recorded compaction round."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetCompactionRoundUseCaseInput,
)
from context.table_maintenance.application.service.compaction_round import GetCompactionRoundService
from tests.context.table_maintenance.application.service.compaction_round.recorded_round import recorded_round
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def test_reads_a_recorded_round(tables_repo):
    """A recorded round is read with its budget, picks and skips."""
    rounds = InMemoryCompactionRoundsRepo()
    rounds.save(recorded_round("round-1", NOW))

    out = GetCompactionRoundService(rounds, tables_repo).execute(GetCompactionRoundUseCaseInput(round_id="round-1"))

    assert (
        out.round_id,
        out.started_at,
        out.budget_gb_hours,
        out.used_gb_hours,
        out.skipped_total,
        out.busy_skipped,
    ) == ("round-1", NOW, 0.05, 0.04, 3, 4)
    assert [(p.table_uuid, p.table_name, p.priority, p.overdue) for p in out.picks] == [("t-1", None, "P0", True)]
    assert [(s.table_uuid, s.spec_id, s.reason) for s in out.skips] == [("t-2", -1, "budget_used")]


def test_an_unknown_round_is_not_found(tables_repo):
    """A round never recorded, or purged, is a not-found error."""
    with pytest.raises(NotFoundError):
        GetCompactionRoundService(InMemoryCompactionRoundsRepo(), tables_repo).execute(
            GetCompactionRoundUseCaseInput(round_id="nope")
        )
