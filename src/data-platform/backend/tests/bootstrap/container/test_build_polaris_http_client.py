"""Test that the Polaris HTTP client is built from the catalog settings."""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
from pydantic import SecretStr

from bootstrap.configs import CatalogSettings
from bootstrap.container import build_polaris_http_client


def test_client_uses_the_catalog_settings():
    """The token goes to the catalog URI with the credential and scope; management calls go to the management URI."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(200, json={"catalogs": []})

    settings = CatalogSettings(
        uri="http://polaris:8181/api/catalog",
        management_uri="http://polaris:8181/api/management/v1",
        credential=SecretStr("root:s3cr3t"),
        scope="PRINCIPAL_ROLE:ALL",
    )

    client = build_polaris_http_client(settings, transport=httpx.MockTransport(handle))
    client.management_request("GET", "/catalogs")

    token, listing = seen
    assert str(token.url) == "http://polaris:8181/api/catalog/v1/oauth/tokens"
    form = {key: values[0] for key, values in parse_qs(token.content.decode()).items()}
    assert (form["client_id"], form["client_secret"], form["scope"]) == ("root", "s3cr3t", "PRINCIPAL_ROLE:ALL")
    assert str(listing.url) == "http://polaris:8181/api/management/v1/catalogs"


def test_client_is_built_without_contacting_polaris():
    """Building the client sends nothing; the token is fetched on first use."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(500)

    build_polaris_http_client(CatalogSettings(), transport=httpx.MockTransport(handle))

    assert seen == []
