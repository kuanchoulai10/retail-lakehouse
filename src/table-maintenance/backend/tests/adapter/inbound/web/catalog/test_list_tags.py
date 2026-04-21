"""Tests for list tags endpoint."""

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


def test_list_tags_returns_200():
    """Return 200 with a list of tag refs."""
    mock = MagicMock()
    mock.list_tags.return_value = [
        {
            "name": "v1.0",
            "snapshot_id": 200,
            "max_ref_age_ms": None,
        },
    ]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["name"] == "v1.0"
    assert body["tags"][0]["snapshot_id"] == 200
    mock.list_tags.assert_called_once_with("default", "orders")


def test_list_tags_empty():
    """Return 200 with empty list when table has no tags."""
    mock = MagicMock()
    mock.list_tags.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    assert response.json() == {"tags": []}
