"""Tests for list branches endpoint."""

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


def test_list_branches_returns_200():
    """Return 200 with a list of branch refs."""
    mock = MagicMock()
    mock.list_branches.return_value = [
        {
            "name": "main",
            "snapshot_id": 100,
            "max_snapshot_age_ms": None,
            "max_ref_age_ms": None,
            "min_snapshots_to_keep": None,
        },
    ]
    client = _make_client(mock)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/branches"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["branches"]) == 1
    assert body["branches"][0]["name"] == "main"
    assert body["branches"][0]["snapshot_id"] == 100
    mock.list_branches.assert_called_once_with("default", "orders")


def test_list_branches_empty():
    """Return 200 with empty list when table has no branches."""
    mock = MagicMock()
    mock.list_branches.return_value = []
    client = _make_client(mock)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/branches"
    )

    assert response.status_code == 200
    assert response.json() == {"branches": []}
