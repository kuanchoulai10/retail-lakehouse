"""Pin that table maintenance no longer serves a table's health or storage; the Overview cards replace them."""

from __future__ import annotations

import pytest

from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client


@pytest.mark.parametrize("path", ["health", "storage"])
def test_health_and_storage_routes_are_gone(path: str) -> None:
    """GET /v1/tables/{uuid}/health and /storage are not routes any more."""
    client = build_client()

    response = client.get(f"/v1/tables/u-1/{path}")

    assert response.status_code in (404, 405)
