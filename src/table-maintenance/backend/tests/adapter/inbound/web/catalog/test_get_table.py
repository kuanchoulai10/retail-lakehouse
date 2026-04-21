"""Tests for get table metadata endpoint."""

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


SAMPLE_TABLE = {
    "table": "orders",
    "namespace": "default",
    "location": "s3://warehouse/default/orders",
    "current_snapshot_id": 123,
    "schema": {
        "fields": [
            {"id": 1, "name": "order_id", "type": "long", "required": True},
        ],
    },
    "properties": {"write.format.default": "parquet"},
}


def test_get_table_returns_200():
    """Return 200 with table metadata."""
    mock = MagicMock()
    mock.get_table.return_value = SAMPLE_TABLE
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders")

    assert response.status_code == 200
    body = response.json()
    assert body["table"] == "orders"
    assert body["namespace"] == "default"
    assert body["location"] == "s3://warehouse/default/orders"
    assert body["current_snapshot_id"] == 123
    assert len(body["schema"]["fields"]) == 1
    assert body["schema"]["fields"][0]["name"] == "order_id"
    mock.get_table.assert_called_once_with("default", "orders")
