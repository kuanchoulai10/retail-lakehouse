"""Test that walking every namespace refuses replies it cannot read."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.shared.polaris import walk_iceberg_namespaces
from context.catalog.application.exceptions import CatalogUnavailableError
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

CATALOGS = "/api/management/v1/catalogs"
NAMESPACES = "/api/catalog/v1/sales/namespaces"
_HTML = httpx.Response(200, text="<html>proxy error</html>", headers={"content-type": "text/html"})


def test_walk_returns_each_namespace_after_its_parent():
    """Every catalog is walked level by level."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on(
        "GET",
        NAMESPACES,
        httpx.Response(200, json={"namespaces": [["a"]]}),
        httpx.Response(200, json={"namespaces": []}),
    )

    assert walk_iceberg_namespaces(stub.client()) == [("sales", ("a",))]


@pytest.mark.parametrize(
    "reply",
    [_HTML, httpx.Response(200, json=["sales"]), httpx.Response(200, json={"catalogs": ["sales"]})],
    ids=["html", "json-list", "string-item"],
)
def test_unreadable_catalog_list_is_unavailable(reply: httpx.Response):
    """A catalog list that is not an object of named catalogs is a 502."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, reply)

    with pytest.raises(CatalogUnavailableError, match="the catalog list in a form this backend cannot read"):
        walk_iceberg_namespaces(stub.client())


@pytest.mark.parametrize("body", [["a"], {"namespaces": ["a"]}, {}], ids=["json-list", "string-item", "missing"])
def test_unreadable_namespace_listing_is_unavailable(body: Any):  # noqa: ANN401
    """A namespace listing that is not a list of string lists is a 502, never single characters."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on("GET", NAMESPACES, httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="the namespaces of catalog sales in a form this backend"):
        walk_iceberg_namespaces(stub.client())
