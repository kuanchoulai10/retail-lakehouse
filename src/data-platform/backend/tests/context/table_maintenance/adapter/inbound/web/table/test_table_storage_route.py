"""Test the table storage route with a stub use case."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table import (
    GetTableStorageUseCaseInput,
    GetTableStorageUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)


def test_get_storage_returns_200() -> None:
    """The storage route returns the current bytes and old snapshot files."""
    output = GetTableStorageUseCaseOutput(
        current_bytes=1000,
        current_files=10,
        old_snapshot_bytes=3000,
        old_snapshot_files=15,
        window_days=30,
        reclaimed={"rewritten_data_files": 20, "expired_snapshots": 22},
        attempts_without_metrics=1,
    )
    stub = StubUseCase(output)
    client = build_client(get_table_storage=stub)

    response = client.get("/v1/tables/u-1/storage")

    body = response.json()
    assert response.status_code == 200
    assert body["current_bytes"] == 1000
    assert body["old_snapshot_files"] == 15
    assert body["window_days"] == 30
    assert body["reclaimed"]["expired_snapshots"] == 22
    assert body["attempts_without_metrics"] == 1
    assert stub.requests == [GetTableStorageUseCaseInput(uuid="u-1")]
