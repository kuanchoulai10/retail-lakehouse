"""Test the compaction round routes."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetCompactionRoundUseCaseOutput,
    GetCompactionRoundUseCaseOutputPick,
    GetCompactionRoundUseCaseOutputSkip,
    ListCompactionRoundsUseCaseInput,
    ListCompactionRoundsUseCaseOutput,
    ListCompactionRoundsUseCaseOutputItem,
    ListCompactionRoundsUseCaseOutputPick,
    ListCompactionRoundsUseCaseOutputSkip,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

PICK_JSON = {
    "table_uuid": "t-1",
    "table_name": "iceberg.sales.orders",
    "partition": {"spec_id": 0, "values": ["2026-11-01"]},
    "partition_label": "day=2026-11-01",
    "priority": "P0",
    "score": 0.5,
    "weighted_score": 2.0,
    "estimated_gb_hours": 0.04,
    "overdue": True,
}
SKIP_JSON = {
    "table_uuid": "t-2",
    "table_name": None,
    "partition": {"spec_id": -1, "values": []},
    "partition_label": "whole table",
    "priority": "P2",
    "score": 0.6,
    "weighted_score": 0.6,
    "estimated_gb_hours": 0.03,
    "overdue": False,
    "reason": "budget_used",
}
ROUND_JSON = {
    "round_id": "compaction-rounds-1",
    "started_at": "2026-11-13T12:00:00Z",
    "budget_gb_hours": 0.05,
    "used_gb_hours": 0.04,
    "picks": [PICK_JSON],
    "skips": [SKIP_JSON],
    "skipped_total": 3,
}


def _listed() -> ListCompactionRoundsUseCaseOutputItem:
    return ListCompactionRoundsUseCaseOutputItem(
        round_id="compaction-rounds-1",
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.04,
        picks=[
            ListCompactionRoundsUseCaseOutputPick(
                table_uuid="t-1",
                table_name="iceberg.sales.orders",
                spec_id=0,
                values=["2026-11-01"],
                partition_label="day=2026-11-01",
                priority="P0",
                score=0.5,
                weighted_score=2.0,
                estimated_gb_hours=0.04,
                overdue=True,
            )
        ],
        skips=[
            ListCompactionRoundsUseCaseOutputSkip(
                table_uuid="t-2",
                table_name=None,
                spec_id=-1,
                values=[],
                partition_label="whole table",
                priority="P2",
                score=0.6,
                weighted_score=0.6,
                estimated_gb_hours=0.03,
                overdue=False,
                reason="budget_used",
            )
        ],
        skipped_total=3,
    )


def test_lists_rounds_newest_first_with_picks_and_skips():
    """The list route answers the use case's rounds with their picks and skips."""
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=[_listed()]))

    response = build_client(list_compaction_rounds=stub).get("/v1/compaction-rounds")

    assert response.status_code == 200
    assert response.json() == [ROUND_JSON]
    assert stub.requests == [ListCompactionRoundsUseCaseInput(limit=50, before=None)]


def test_limit_and_before_reach_the_use_case():
    """``limit`` and ``before`` page through older rounds."""
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=[]))

    response = build_client(list_compaction_rounds=stub).get(
        "/v1/compaction-rounds", params={"limit": 5, "before": "2026-11-13T12:00:00Z"}
    )

    assert response.status_code == 200
    assert stub.requests == [ListCompactionRoundsUseCaseInput(limit=5, before=NOW)]


def test_a_limit_out_of_range_is_422():
    """A limit below 1 or above 200 is refused."""
    client = build_client(list_compaction_rounds=StubUseCase(ListCompactionRoundsUseCaseOutput(items=[])))

    assert client.get("/v1/compaction-rounds", params={"limit": 0}).status_code == 422
    assert client.get("/v1/compaction-rounds", params={"limit": 201}).status_code == 422


def test_gets_one_round():
    """The get route answers one round by id."""
    stub = StubUseCase(
        GetCompactionRoundUseCaseOutput(
            round_id="compaction-rounds-1",
            started_at=NOW,
            budget_gb_hours=0.05,
            used_gb_hours=0.04,
            picks=[GetCompactionRoundUseCaseOutputPick(**vars(_listed().picks[0]))],
            skips=[GetCompactionRoundUseCaseOutputSkip(**vars(_listed().skips[0]))],
            skipped_total=3,
        )
    )

    response = build_client(get_compaction_round=stub).get("/v1/compaction-rounds/compaction-rounds-1")

    assert response.status_code == 200
    assert response.json() == ROUND_JSON
    assert stub.requests[0].round_id == "compaction-rounds-1"


def test_an_unknown_round_is_404():
    """A round never recorded, or purged, answers 404."""
    client = build_client(get_compaction_round=StubUseCase(error=NotFoundError("compaction round nope not found")))

    assert client.get("/v1/compaction-rounds/nope").status_code == 404


def test_a_busy_table_skip_is_served():
    """A skip because the table is busy reaches the client with its reason."""
    listed = _listed()
    listed = replace(listed, skips=[replace(listed.skips[0], reason="table_busy")])
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=[listed]))

    response = build_client(list_compaction_rounds=stub).get("/v1/compaction-rounds")

    assert response.status_code == 200
    assert response.json()[0]["skips"][0]["reason"] == "table_busy"
