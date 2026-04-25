"""Tests for list tags endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router
from core.application.port.inbound.catalog.list_tags.output import (
    ListTagsOutput,
    ListTagsOutputItem,
)
from dependencies.use_cases import get_list_tags_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_tags_use_case] = lambda: use_case
    return TestClient(app)


def test_list_tags_returns_200():
    """Return 200 with a list of tag refs."""
    use_case = MagicMock()
    use_case.execute.return_value = ListTagsOutput(
        tags=[
            ListTagsOutputItem(name="v1.0", snapshot_id=200, max_ref_age_ms=None),
        ],
    )
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["name"] == "v1.0"
    assert body["tags"][0]["snapshot_id"] == 200


def test_list_tags_empty():
    """Return 200 with empty list when table has no tags."""
    use_case = MagicMock()
    use_case.execute.return_value = ListTagsOutput(tags=[])
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    assert response.json() == {"tags": []}
