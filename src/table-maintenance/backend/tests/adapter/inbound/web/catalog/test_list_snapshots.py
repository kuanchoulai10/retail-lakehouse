"""Tests for list snapshots endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_snapshots_returns_200():
    """Return 200 with a list of snapshots."""
    mock = MagicMock()
    mock.list_snapshots.return_value = [
        {
            "snapshot_id": 100,
            "parent_id": None,
            "timestamp_ms": 1713600000000,
            "summary": {"operation": "append", "added-records": "50"},
        },
    ]
    client = _make_client(mock)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["snapshots"]) == 1
    assert body["snapshots"][0]["snapshot_id"] == 100
    assert body["snapshots"][0]["parent_id"] is None
    assert body["snapshots"][0]["summary"]["operation"] == "append"
    mock.list_snapshots.assert_called_once_with("default", "orders")


def test_list_snapshots_empty():
    """Return 200 with empty list when table has no snapshots."""
    mock = MagicMock()
    mock.list_snapshots.return_value = []
    client = _make_client(mock)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots"
    )

    assert response.status_code == 200
    assert response.json() == {"snapshots": []}
