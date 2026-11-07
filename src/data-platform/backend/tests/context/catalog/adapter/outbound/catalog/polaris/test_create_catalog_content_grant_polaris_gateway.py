"""Test that the content grant gateway grants CATALOG_MANAGE_CONTENT to the catalog's catalog_admin role."""

from __future__ import annotations

import json

import httpx
import pytest

from context.catalog.adapter.outbound.catalog.polaris import (
    CreateCatalogContentGrantPolarisGateway,
)
from context.catalog.application.exceptions import PermissionDeniedError
from context.catalog.application.port.outbound.catalog import (
    CreateCatalogContentGrantGatewayInput,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import (
    PolarisStub,
)

GRANTS = "/api/management/v1/catalogs/sales/catalog-roles/catalog_admin/grants"


def test_grant_puts_catalog_manage_content_on_catalog_admin():
    """The grant is PUT on the catalog_admin role of the named catalog."""
    stub = PolarisStub()
    stub.on("PUT", GRANTS, httpx.Response(201))

    CreateCatalogContentGrantPolarisGateway(stub.client()).create(
        CreateCatalogContentGrantGatewayInput(catalog_name="sales")
    )

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("PUT", GRANTS)
    assert json.loads(request.content) == {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}


def test_refused_grant_raises_with_polaris_message():
    """Polaris refusing the grant reaches the caller with its message."""
    stub = PolarisStub()
    stub.on("PUT", GRANTS, httpx.Response(403, json={"error": {"message": "not authorized for op ADD_GRANT"}}))

    with pytest.raises(PermissionDeniedError, match="not authorized for op ADD_GRANT"):
        CreateCatalogContentGrantPolarisGateway(stub.client()).create(
            CreateCatalogContentGrantGatewayInput(catalog_name="sales")
        )
