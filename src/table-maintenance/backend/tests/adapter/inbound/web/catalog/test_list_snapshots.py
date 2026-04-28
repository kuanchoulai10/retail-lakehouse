"""Tests for list snapshots endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router
from application.port.inbound.catalog.list_snapshots.output import (
    ListSnapshotsUseCaseOutput,
    ListSnapshotsUseCaseOutputItem,
)
from bootstrap.dependencies.use_cases import get_list_snapshots_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_snapshots_use_case] = lambda: use_case
    return TestClient(app)


def test_list_snapshots_returns_200():
    """Return 200 with a list of snapshots."""
    use_case = MagicMock()
    use_case.execute.return_value = ListSnapshotsUseCaseOutput(
        snapshots=[
            ListSnapshotsUseCaseOutputItem(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=1713600000000,
                summary={"operation": "append", "added-records": "50"},
            ),
        ],
    )
    client = _make_client(use_case)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["snapshots"]) == 1
    assert body["snapshots"][0]["snapshot_id"] == 100
    assert body["snapshots"][0]["parent_id"] is None
    assert body["snapshots"][0]["summary"]["operation"] == "append"


def test_list_snapshots_empty():
    """Return 200 with empty list when table has no snapshots."""
    use_case = MagicMock()
    use_case.execute.return_value = ListSnapshotsUseCaseOutput(snapshots=[])
    client = _make_client(use_case)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots"
    )

    assert response.status_code == 200
    assert response.json() == {"snapshots": []}
