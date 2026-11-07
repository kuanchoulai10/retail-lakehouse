"""Test the table health route with a stub use case."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table import (
    GetTableHealthUseCaseInput,
    GetTableHealthUseCaseOutput,
    GetTableHealthUseCaseOutputItem,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)


def _item(operation, verdict, next_eligible_at=None):
    return GetTableHealthUseCaseOutputItem(
        operation=operation,
        verdict=verdict,
        measured=12,
        threshold=5,
        next_eligible_at=next_eligible_at,
        qualifying_partitions=None,
        size_bytes=None,
        size_source=None,
    )


def test_get_health_returns_verdict_strings() -> None:
    """The health route returns each operation verdict as a string with its next eligible time."""
    output = GetTableHealthUseCaseOutput(
        scheduled=True,
        not_scheduled_reason=None,
        operations=[
            _item("rewrite_data_files", "due"),
            _item("expire_snapshots", "cooldown", NOW),
        ],
        position_delete_files=2,
        equality_delete_files=1,
    )
    stub = StubUseCase(output)
    client = build_client(get_table_health=stub)

    response = client.get("/v1/tables/u-1/health")

    body = response.json()
    assert response.status_code == 200
    assert [o["verdict"] for o in body["operations"]] == ["due", "cooldown"]
    assert body["operations"][1]["next_eligible_at"].startswith("2026-10-24T12:00")
    assert body["position_delete_files"] == 2
    assert stub.requests == [GetTableHealthUseCaseInput(uuid="u-1")]
