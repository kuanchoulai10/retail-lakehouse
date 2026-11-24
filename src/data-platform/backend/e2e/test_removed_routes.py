"""Routes the platform removed are gone: they answer FastAPI's own 404, not a 405 or a handler's 404."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx

pytestmark = pytest.mark.critical

TABLE = "00000000-0000-4000-8000-000000000000"
REMOVED = [
    ("GET", "/v1/maintenance-policies/default/mappings"),
    ("PUT", "/v1/maintenance-policies/default/mappings"),
    ("DELETE", "/v1/maintenance-policies/default/mappings"),
    ("GET", f"/v1/tables/{TABLE}/applicable-policy"),
    ("GET", "/v1/applicable-policy?catalog=iceberg"),
    ("GET", "/v1/discovery-rules"),
    ("GET", "/v1/discovery-rules/catalogs"),
    ("GET", "/v1/compaction-rounds"),
    ("GET", f"/v1/tables/{TABLE}/health"),
    ("GET", f"/v1/tables/{TABLE}/storage"),
]


@pytest.mark.parametrize(("method", "path"), REMOVED)
def test_a_removed_route_is_not_found(api: httpx.Client, method: str, path: str):
    """No route matches the path: ``Not Found`` is the router's answer, which no handler's 404 gives."""
    reply = api.request(method, path)
    assert (reply.status_code, reply.json()) == (404, {"detail": "Not Found"}), reply.text
