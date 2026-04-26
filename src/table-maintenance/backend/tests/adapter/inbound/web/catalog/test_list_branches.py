"""Tests for list branches endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapter.inbound.web import router
from core.application.port.inbound.catalog.list_branches.output import (
    ListBranchesOutput,
    ListBranchesOutputItem,
)
from dependencies.use_cases import get_list_branches_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_branches_use_case] = lambda: use_case
    return TestClient(app)


def test_list_branches_returns_200():
    """Return 200 with a list of branch refs."""
    use_case = MagicMock()
    use_case.execute.return_value = ListBranchesOutput(
        branches=[
            ListBranchesOutputItem(
                name="main",
                snapshot_id=100,
                max_snapshot_age_ms=None,
                max_ref_age_ms=None,
                min_snapshots_to_keep=None,
            ),
        ],
    )
    client = _make_client(use_case)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/branches"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["branches"]) == 1
    assert body["branches"][0]["name"] == "main"
    assert body["branches"][0]["snapshot_id"] == 100


def test_list_branches_empty():
    """Return 200 with empty list when table has no branches."""
    use_case = MagicMock()
    use_case.execute.return_value = ListBranchesOutput(branches=[])
    client = _make_client(use_case)

    response = client.get(
        "/v1/catalogs/iceberg/namespaces/default/tables/orders/branches"
    )

    assert response.status_code == 200
    assert response.json() == {"branches": []}
