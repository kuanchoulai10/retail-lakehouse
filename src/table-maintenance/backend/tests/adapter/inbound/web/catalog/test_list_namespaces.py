"""Tests for list namespaces endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapter.inbound.web import router
from application.port.inbound.catalog.list_namespaces import ListNamespacesOutput
from bootstrap.dependencies.use_cases import get_list_namespaces_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_namespaces_use_case] = lambda: use_case
    return TestClient(app)


def test_list_namespaces_returns_200():
    """Return 200 with a list of namespace names."""
    use_case = MagicMock()
    use_case.execute.return_value = ListNamespacesOutput(namespaces=["default", "raw"])
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces")

    assert response.status_code == 200
    assert response.json() == {"namespaces": ["default", "raw"]}


def test_list_namespaces_empty():
    """Return 200 with an empty list when no namespaces exist."""
    use_case = MagicMock()
    use_case.execute.return_value = ListNamespacesOutput(namespaces=[])
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces")

    assert response.status_code == 200
    assert response.json() == {"namespaces": []}
