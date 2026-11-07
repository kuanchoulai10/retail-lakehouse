"""Pin that table maintenance no longer serves table metadata; the catalog context does."""

from __future__ import annotations

from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client


def test_table_metadata_route_is_gone() -> None:
    """GET /v1/tables/{uuid}/metadata is not a route any more."""
    client = build_client()

    response = client.get("/v1/tables/u-1/metadata")

    assert response.status_code in (404, 405)
