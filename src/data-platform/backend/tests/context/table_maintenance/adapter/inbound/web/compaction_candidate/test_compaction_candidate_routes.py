"""Test the compaction candidate routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCaseOutput,
    ListCompactionCandidatesUseCaseOutputItem,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


def _item(rank: int | None, state: str = "pending") -> ListCompactionCandidatesUseCaseOutputItem:
    return ListCompactionCandidatesUseCaseOutputItem(
        spec_id=0,
        values=["2026-11-01"],
        partition_label="day=2026-11-01",
        state=state,
        hold_reason=None,
        reducible_files=12,
        data_bytes=4096,
        estimated_gb_hours=0.5,
        score=0.62,
        rank=rank,
        claimed_by_run_id=None,
        lease_expires_at=None,
        last_written_at=NOW - timedelta(hours=1),
        observed_at=NOW,
        priority="P1",
        granted_round_id="compaction-rounds-1" if state == "granted" else None,
        pending_since=NOW - timedelta(hours=5),
        overdue=True,
        granted_round_started_at=NOW - timedelta(minutes=1) if state == "granted" else None,
    )


def test_lists_a_tables_candidates_with_how_many_one_run_takes():
    """The route answers the table's candidates in the use case's order, with partitions per run."""
    stub = StubUseCase(ListCompactionCandidatesUseCaseOutput(partitions_per_run=10, items=[_item(1)]))
    client = build_client(list_compaction_candidates=stub)

    response = client.get("/v1/tables/u-1/compaction-candidates")

    assert response.status_code == 200
    assert stub.requests[0].table_uuid == "u-1"
    assert response.json() == {
        "partitions_per_run": 10,
        "candidates": [
            {
                "partition": {"spec_id": 0, "values": ["2026-11-01"]},
                "partition_label": "day=2026-11-01",
                "state": "pending",
                "hold_reason": None,
                "reducible_files": 12,
                "data_bytes": 4096,
                "estimated_gb_hours": 0.5,
                "score": 0.62,
                "rank": 1,
                "claimed_by_run_id": None,
                "lease_expires_at": None,
                "last_written_at": "2026-11-13T11:00:00Z",
                "observed_at": "2026-11-13T12:00:00Z",
                "priority": "P1",
                "granted_round_id": None,
                "pending_since": "2026-11-13T07:00:00Z",
                "overdue": True,
                "granted_round_started_at": None,
            }
        ],
    }


def test_a_granted_candidate_names_its_round():
    """A granted candidate carries the round that granted it."""
    stub = StubUseCase(ListCompactionCandidatesUseCaseOutput(partitions_per_run=10, items=[_item(None, "granted")]))

    candidate = build_client(list_compaction_candidates=stub).get("/v1/tables/u-1/compaction-candidates").json()

    (granted,) = candidate["candidates"]
    assert (granted["state"], granted["granted_round_id"], granted["granted_round_started_at"]) == (
        "granted",
        "compaction-rounds-1",
        "2026-11-13T11:59:00Z",
    )


def test_unknown_table_is_404():
    """A table maintenance does not know answers 404."""
    client = build_client(list_compaction_candidates=StubUseCase(error=NotFoundError("table nope not found")))

    assert client.get("/v1/tables/nope/compaction-candidates").status_code == 404
