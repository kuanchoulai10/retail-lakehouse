"""Test PolarisClient, which calls Polaris's catalog and management APIs with one principal's token."""

from __future__ import annotations

import json
import urllib.parse

import httpx

from e2e.support import PolarisClient

CATALOG = "http://polaris:8181/api/catalog"
MANAGEMENT = "http://polaris:8181/api/management/v1"


def _client(seen: list[httpx.Request]) -> PolarisClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/catalog/v1/oauth/tokens":
            return httpx.Response(200, json={"access_token": f"token-{len(seen)}"})
        return httpx.Response(200, json={"ok": True})

    return PolarisClient(
        httpx.Client(transport=httpx.MockTransport(handle)),
        catalog_uri=CATALOG,
        management_uri=MANAGEMENT,
        credential="the-id:the-secret",
        scope="PRINCIPAL_ROLE:ALL",
    )


def test_asks_for_a_token_with_the_principal_credential_once():
    """The first call gets a client-credentials token; later calls reuse it."""
    seen: list[httpx.Request] = []
    polaris = _client(seen)
    polaris.management("GET", "/catalogs")
    polaris.catalog("GET", "/v1/iceberg/namespaces")
    form = urllib.parse.parse_qs(seen[0].content.decode())
    assert form == {
        "grant_type": ["client_credentials"],
        "client_id": ["the-id"],
        "client_secret": ["the-secret"],
        "scope": ["PRINCIPAL_ROLE:ALL"],
    }
    assert [request.url.path for request in seen] == [
        "/api/catalog/v1/oauth/tokens",
        "/api/management/v1/catalogs",
        "/api/catalog/v1/iceberg/namespaces",
    ]
    assert {request.headers["Authorization"] for request in seen[1:]} == {"Bearer token-1"}


def test_sends_a_json_body():
    """A body goes as JSON."""
    seen: list[httpx.Request] = []
    _client(seen).management("POST", "/principals", json={"principal": {"name": "tm-e2e"}})
    assert json.loads(seen[1].content) == {"principal": {"name": "tm-e2e"}}
    assert seen[1].method == "POST"
