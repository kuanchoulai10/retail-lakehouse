"""Test the compaction round routes."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.port.inbound.compaction_round import (
    GetCompactionRoundUseCaseOutput,
    ListCompactionRoundsUseCaseInput,
    ListCompactionRoundsUseCaseOutput,
)
from context.table_maintenance.application.service.compaction_round import GetCompactionRoundService
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

ROUND_1 = "cr-00000000000000000000000001"
UNKNOWN_ROUND = "cr-00000000000000000000000099"
OLD_WORKFLOW_ROUND_ID = "compaction-rounds-2026-11-13T12:00:00Z"
ROUND_ID_SHAPE = "CompactionRoundId must look like cr-<26 base32 characters>"

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

PICK_JSON = {
    "table_uuid": "t-1",
    "table_name": "iceberg.sales.orders",
    "table": {"catalog": "iceberg", "namespace": ["sales"], "name": "orders"},
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
    "table": None,
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
    "round_id": ROUND_1,
    "started_at": "2026-11-13T12:00:00Z",
    "budget_gb_hours": 0.05,
    "used_gb_hours": 0.04,
    "picks": [PICK_JSON],
    "skips": [SKIP_JSON],
    "skipped_total": 3,
    "busy_skipped": 4,
}


def _listed() -> ListCompactionRoundsUseCaseOutput.CompactionRound:
    return ListCompactionRoundsUseCaseOutput.CompactionRound(
        round_id=ROUND_1,
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.04,
        picks=(
            ListCompactionRoundsUseCaseOutput.Pick(
                table_uuid="t-1",
                table_name="iceberg.sales.orders",
                spec_id=0,
                values=("2026-11-01",),
                partition_label="day=2026-11-01",
                priority="P0",
                score=0.5,
                weighted_score=2.0,
                estimated_gb_hours=0.04,
                overdue=True,
                catalog="iceberg",
                namespace=("sales",),
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


def test_lists_rounds_newest_first_with_picks_and_skips():
    """The list route answers the use case's rounds with their picks and skips."""
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=(_listed(),)))

    response = build_client(list_compaction_rounds=stub).get("/v1/compaction-rounds")

    assert response.status_code == 200
    assert response.json() == [ROUND_JSON]
    assert stub.requests == [ListCompactionRoundsUseCaseInput(limit=50, before=None)]


def test_limit_and_before_reach_the_use_case():
    """``limit`` and ``before`` page through older rounds."""
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=()))

    response = build_client(list_compaction_rounds=stub).get(
        "/v1/compaction-rounds", params={"limit": 5, "before": "2026-11-13T12:00:00Z"}
    )

    assert response.status_code == 200
    assert stub.requests == [ListCompactionRoundsUseCaseInput(limit=5, before=NOW)]


def test_a_limit_out_of_range_is_422():
    """A limit below 1 or above 200 is refused."""
    client = build_client(list_compaction_rounds=StubUseCase(ListCompactionRoundsUseCaseOutput(items=())))

    assert client.get("/v1/compaction-rounds", params={"limit": 0}).status_code == 422
    assert client.get("/v1/compaction-rounds", params={"limit": 201}).status_code == 422


def test_gets_one_round():
    """The get route answers one round by id."""
    stub = StubUseCase(
        GetCompactionRoundUseCaseOutput(
            round_id=ROUND_1,
            started_at=NOW,
            budget_gb_hours=0.05,
            used_gb_hours=0.04,
            picks=(GetCompactionRoundUseCaseOutput.Pick(**vars(_listed().picks[0])),),
            skips=(GetCompactionRoundUseCaseOutput.Skip(**vars(_listed().skips[0])),),
            skipped_total=3,
            busy_skipped=4,
        )
    )

    response = build_client(get_compaction_round=stub).get(f"/v1/compaction-rounds/{ROUND_1}")

    assert response.status_code == 200
    assert response.json() == ROUND_JSON
    assert stub.requests[0].round_id == ROUND_1


def test_an_unknown_round_is_404():
    """A round never recorded, or purged, answers 404."""
    client = build_client(
        get_compaction_round=GetCompactionRoundService(InMemoryCompactionRoundsRepo(), InMemoryTablesRepo())
    )

    assert client.get(f"/v1/compaction-rounds/{UNKNOWN_ROUND}").status_code == 404


def test_a_round_id_of_the_old_workflow_id_shape_is_422():
    """A round id named after its workflow, as rounds were before ``cr-`` ids, answers 422 naming the shape."""
    client = build_client(
        get_compaction_round=GetCompactionRoundService(InMemoryCompactionRoundsRepo(), InMemoryTablesRepo())
    )

    response = client.get(f"/v1/compaction-rounds/{OLD_WORKFLOW_ROUND_ID}")

    assert response.status_code == 422
    assert ROUND_ID_SHAPE in response.json()["detail"]


def test_a_busy_table_skip_is_served():
    """A skip because the table is busy reaches the client with its reason."""
    listed = _listed()
    busy = ListCompactionRoundsUseCaseOutput.Skip(**(listed.skips[0].model_dump() | {"reason": "table_busy"}))
    listed = ListCompactionRoundsUseCaseOutput.CompactionRound(**(listed.model_dump() | {"skips": (busy,)}))
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=(listed,)))

    response = build_client(list_compaction_rounds=stub).get("/v1/compaction-rounds")

    assert response.status_code == 200
    assert response.json()[0]["skips"][0]["reason"] == "table_busy"


def test_a_before_without_a_time_zone_is_422():
    """A cursor with no offset is refused instead of failing inside the store."""
    stub = StubUseCase(ListCompactionRoundsUseCaseOutput(items=()))

    response = build_client(list_compaction_rounds=stub).get(
        "/v1/compaction-rounds", params={"before": "2026-11-13T12:00:00"}
    )

    assert response.status_code == 422
    assert stub.requests == []


def test_round_id_path_parameter_describes_its_shape() -> None:
    """The ``round_id`` parameter tells an API user the ``cr-`` shape, with no pattern of its own."""
    operation = build_client().get("/openapi.json").json()["paths"]["/v1/compaction-rounds/{round_id}"]["get"]
    parameter = next(p for p in operation["parameters"] if p["name"] == "round_id")
    assert "`cr-`" in parameter["description"]
    assert "ADR 0011" in parameter["description"]
    assert "pattern" not in parameter["schema"]
