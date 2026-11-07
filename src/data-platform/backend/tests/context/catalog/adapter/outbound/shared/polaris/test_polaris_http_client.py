"""Test the Polaris HTTP client: token handling, routing and error mapping."""

from __future__ import annotations

import httpx
import pytest

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    PermissionDeniedError,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import (
    PolarisStub,
)

CATALOGS = "/api/management/v1/catalogs"


def test_token_fetched_with_client_credentials_and_scope():
    """The first request fetches a client-credentials token with the scope; later requests reuse it."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": []}))
    client = stub.client()

    assert stub.token_requests == []
    client.management_request("GET", "/catalogs")
    client.management_request("GET", "/catalogs")

    assert len(stub.token_requests) == 1
    assert PolarisStub.form(stub.token_requests[0]) == {
        "grant_type": "client_credentials",
        "client_id": "root",
        "client_secret": "s3cr3t",
        "scope": "PRINCIPAL_ROLE:ALL",
    }
    assert [r.headers["Authorization"] for r in stub.requests] == ["Bearer tok-1", "Bearer tok-1"]


def test_expired_token_is_refreshed_once():
    """A 401 drops the token, fetches a new one and retries the request once with it."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(401), httpx.Response(200, json={"catalogs": []}))

    response = stub.client().management_request("GET", "/catalogs")

    assert response.json() == {"catalogs": []}
    assert len(stub.token_requests) == 2
    assert [r.headers["Authorization"] for r in stub.requests] == ["Bearer tok-1", "Bearer tok-2"]


def test_refreshed_token_rejected_again_is_not_retried_twice():
    """A second 401 after the refresh is reported as permission denied, without another retry."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(401, json={"error": {"message": "token rejected"}}))

    with pytest.raises(PermissionDeniedError, match="token rejected"):
        stub.client().management_request("GET", "/catalogs")

    assert len(stub.token_requests) == 2
    assert len(stub.requests) == 2


def test_connect_error_maps_to_unavailable():
    """A Polaris that cannot be reached is reported as unavailable."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.ConnectError("connection refused"))

    with pytest.raises(CatalogUnavailableError, match="connection refused"):
        stub.client().management_request("GET", "/catalogs")


def test_failed_token_fetch_is_unavailable_and_retried_on_the_next_request():
    """A token fetch that fails is reported as unavailable, and the next request fetches a token again."""
    stub = PolarisStub()
    stub.fail_token(httpx.ConnectError("polaris down"))
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": []}))
    client = stub.client()

    with pytest.raises(CatalogUnavailableError, match="polaris down"):
        client.management_request("GET", "/catalogs")
    client.management_request("GET", "/catalogs")

    assert len(stub.token_requests) == 2
    assert [r.headers["Authorization"] for r in stub.requests] == ["Bearer tok-1"]


def test_rejected_credential_is_unavailable_not_permission_denied():
    """Polaris refusing the backend's own credential is an upstream failure, not the user's missing privilege."""
    stub = PolarisStub()
    stub.fail_token(httpx.Response(401, json={"error": {"message": "invalid client"}}))

    with pytest.raises(CatalogUnavailableError, match="invalid client"):
        stub.client().management_request("GET", "/catalogs")


def test_token_response_without_access_token_is_unavailable():
    """A token response that carries no access token is reported as unavailable."""
    stub = PolarisStub()
    stub.fail_token(httpx.Response(200, json={"token_type": "bearer"}))

    with pytest.raises(CatalogUnavailableError, match="access token"):
        stub.client().management_request("GET", "/catalogs")


def test_error_response_passes_through_the_mapper():
    """Every API response goes through the error mapper."""
    stub = PolarisStub()
    stub.on("POST", CATALOGS, httpx.Response(403, json={"error": {"message": "not allowed", "code": 403}}))

    with pytest.raises(PermissionDeniedError, match="not allowed"):
        stub.client().management_request("POST", "/catalogs", json={"catalog": {}})


def test_catalog_request_paths_are_relative_to_the_catalog_base():
    """Iceberg REST and Polaris generic-table paths both hang off the catalog base URI."""
    stub = PolarisStub()
    stub.on("GET", "/api/catalog/v1/iceberg/namespaces", httpx.Response(200, json={"namespaces": []}))
    stub.on("GET", "/api/catalog/polaris/v1/iceberg/namespaces/a%1Fb/generic-tables", httpx.Response(200, json={}))
    client = stub.client()

    client.catalog_request("GET", "/v1/iceberg/namespaces", params={"parent": "a"})
    client.catalog_request("GET", "/polaris/v1/iceberg/namespaces/a%1Fb/generic-tables")

    assert [str(r.url) for r in stub.requests] == [
        "http://polaris:8181/api/catalog/v1/iceberg/namespaces?parent=a",
        "http://polaris:8181/api/catalog/polaris/v1/iceberg/namespaces/a%1Fb/generic-tables",
    ]


def test_management_request_sends_the_json_body():
    """A management request is sent under the management URI with its JSON body."""
    stub = PolarisStub()
    stub.on("PUT", "/api/management/v1/catalogs/iceberg", httpx.Response(200, json={}))

    stub.client().management_request("PUT", "/catalogs/iceberg", json={"currentEntityVersion": 3})

    (request,) = stub.requests
    assert str(request.url) == "http://polaris:8181/api/management/v1/catalogs/iceberg"
    assert request.headers["Content-Type"] == "application/json"
    assert request.content == b'{"currentEntityVersion":3}'
