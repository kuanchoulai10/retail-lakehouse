"""Test that the catalogs repo sends the exact Polaris management requests and maps the replies."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.catalog.polaris import CatalogsPolarisRepo
from context.catalog.application.exceptions import ConflictError, ValidationError
from context.catalog.application.port.outbound.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
    StorageConfig,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import (
    PolarisStub,
)

CATALOGS = "/api/management/v1/catalogs"
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
NOW_MS = 1794052800000

POLARIS_STORAGE: dict[str, Any] = {
    "storageType": "S3",
    "allowedLocations": ["s3://bucket/"],
    "endpoint": "http://rustfs:9000",
    "pathStyleAccess": True,
}


def _polaris_catalog(name: str = "sales", version: int = 1, **storage: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "type": "INTERNAL",
        "name": name,
        "properties": {"default-base-location": f"s3://bucket/{name}"},
        "createTimestamp": NOW_MS,
        "lastUpdateTimestamp": NOW_MS,
        "entityVersion": version,
        "storageConfigInfo": POLARIS_STORAGE | storage,
    }


def _catalog(name: str = "sales", version: int = 0) -> Catalog:
    return Catalog(
        id=CatalogId.of(name),
        type=CatalogType.INTERNAL,
        properties={"default-base-location": f"s3://bucket/{name}"},
        storage_config=StorageConfig(
            storage_type="S3",
            allowed_locations=("s3://bucket/",),
            endpoint="http://rustfs:9000",
            path_style_access=True,
        ),
        entity_version=version,
    )


def _body(request: httpx.Request) -> Any:  # noqa: ANN401
    return json.loads(request.content)


def test_create_posts_the_catalog_wrapped_in_catalog():
    """Create sends POST /catalogs with ``{"catalog": {...}}`` and returns what Polaris saved."""
    stub = PolarisStub()
    stub.on("POST", CATALOGS, httpx.Response(201, json=_polaris_catalog()))

    saved = CatalogsPolarisRepo(stub.client()).create(_catalog())

    (request,) = stub.requests
    assert request.method == "POST"
    assert request.url.path == CATALOGS
    assert _body(request) == {
        "catalog": {
            "name": "sales",
            "type": "INTERNAL",
            "properties": {"default-base-location": "s3://bucket/sales"},
            "storageConfigInfo": POLARIS_STORAGE,
        }
    }
    assert (saved.id, saved.entity_version, saved.created_at) == (CatalogId.of("sales"), 1, NOW)


def test_update_puts_the_current_entity_version():
    """Update sends PUT /catalogs/{name} with currentEntityVersion, properties and storageConfigInfo."""
    stub = PolarisStub()
    stub.on("PUT", f"{CATALOGS}/sales", httpx.Response(200, json=_polaris_catalog(version=4)))

    saved = CatalogsPolarisRepo(stub.client()).update(_catalog(version=3))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("PUT", f"{CATALOGS}/sales")
    assert _body(request) == {
        "currentEntityVersion": 3,
        "properties": {"default-base-location": "s3://bucket/sales"},
        "storageConfigInfo": POLARIS_STORAGE,
    }
    assert saved.entity_version == 4


def test_update_of_a_stale_version_is_a_conflict():
    """Polaris's 409 on a stale entity version reaches the caller as a conflict."""
    stub = PolarisStub()
    stub.on("PUT", f"{CATALOGS}/sales", httpx.Response(409, json={"error": {"message": "entity version stale"}}))

    with pytest.raises(ConflictError, match="entity version stale"):
        CatalogsPolarisRepo(stub.client()).update(_catalog(version=3))


def test_delete_sends_delete_on_the_catalog():
    """Delete sends DELETE /catalogs/{name}."""
    stub = PolarisStub()
    stub.on("DELETE", f"{CATALOGS}/sales", httpx.Response(204))

    CatalogsPolarisRepo(stub.client()).delete(CatalogId.of("sales"))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("DELETE", f"{CATALOGS}/sales")


def test_delete_of_a_catalog_that_is_not_empty_reports_polaris():
    """Polaris refusing to drop a catalog that still holds content reaches the caller with its message."""
    stub = PolarisStub()
    message = "Catalog 'sales' cannot be dropped, it is not empty"
    stub.on("DELETE", f"{CATALOGS}/sales", httpx.Response(400, json={"error": {"message": message}}))

    with pytest.raises(ValidationError, match=message):
        CatalogsPolarisRepo(stub.client()).delete(CatalogId.of("sales"))


def test_get_maps_every_polaris_field():
    """Get maps the Polaris catalog, its storage config and its timestamps."""
    stub = PolarisStub()
    reply = _polaris_catalog(version=7, userArn="arn:aws:iam::1:user/x", region="us-east-1")
    reply["lastUpdateTimestamp"] = NOW_MS + 1000
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=reply))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("sales"))

    assert catalog is not None
    assert catalog.id == CatalogId.of("sales")
    assert catalog.type is CatalogType.INTERNAL
    assert catalog.properties == {"default-base-location": "s3://bucket/sales"}
    assert catalog.storage_config == StorageConfig(
        storage_type="S3",
        allowed_locations=("s3://bucket/",),
        endpoint="http://rustfs:9000",
        path_style_access=True,
        user_arn="arn:aws:iam::1:user/x",
        region="us-east-1",
    )
    assert catalog.entity_version == 7
    assert catalog.created_at == NOW
    assert catalog.updated_at == datetime(2026, 11, 7, 12, 0, 1, tzinfo=UTC)


def test_get_of_a_missing_catalog_is_none():
    """A 404 from Polaris means the catalog does not exist."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/nope", httpx.Response(404, json={"error": {"message": "Catalog not found: nope"}}))

    assert CatalogsPolarisRepo(stub.client()).get(CatalogId.of("nope")) is None


def test_list_all_returns_every_catalog():
    """List sends GET /catalogs and maps each catalog."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": [_polaris_catalog("a"), _polaris_catalog("b")]}))

    catalogs = CatalogsPolarisRepo(stub.client()).list_all()

    assert [c.id for c in catalogs] == [CatalogId.of("a"), CatalogId.of("b")]


def test_catalog_name_is_percent_encoded_in_the_path():
    """A name with characters that are not URL-safe is encoded as one path segment."""
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/my%20cat%2Fx", httpx.Response(200, json=_polaris_catalog("my cat/x")))

    catalog = CatalogsPolarisRepo(stub.client()).get(CatalogId.of("my cat/x"))

    assert catalog is not None
    assert catalog.id == CatalogId.of("my cat/x")
