"""Tests for list tables endpoint."""

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


def test_list_tables_returns_200():
    """Return 200 with a list of table names."""
    mock = MagicMock()
    mock.list_tables.return_value = ["orders", "products"]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": ["orders", "products"]}
    mock.list_tables.assert_called_once_with("default")


def test_list_tables_empty():
    """Return 200 with an empty list when no tables exist."""
    mock = MagicMock()
    mock.list_tables.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": []}
