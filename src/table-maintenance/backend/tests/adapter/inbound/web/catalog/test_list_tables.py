"""Tests for list tables endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapter.inbound.web import router
from application.port.inbound.catalog.list_tables import ListTablesOutput
from bootstrap.dependencies.use_cases import get_list_tables_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_tables_use_case] = lambda: use_case
    return TestClient(app)


def test_list_tables_returns_200():
    """Return 200 with a list of table names."""
    use_case = MagicMock()
    use_case.execute.return_value = ListTablesOutput(tables=["orders", "products"])
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": ["orders", "products"]}


def test_list_tables_empty():
    """Return 200 with an empty list when no tables exist."""
    use_case = MagicMock()
    use_case.execute.return_value = ListTablesOutput(tables=[])
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": []}
