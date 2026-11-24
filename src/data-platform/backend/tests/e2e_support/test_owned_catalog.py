"""Test OwnedCatalog, a catalog a scenario creates through the platform and drops when it ends."""

from __future__ import annotations

import json
from typing import cast

import httpx
from pyarrow import fs
from pyiceberg.catalog import Catalog

from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, PolarisClient

NAME = "tm_e2e_catalog_1a2b3c4d_lifecycle"
STORAGE = {
    "storage_type": "S3",
    "allowed_locations": ["s3://lake/warehouse"],
    "endpoint": "http://rustfs:9000",
    "sts_endpoint": "http://rustfs:9000",
    "path_style_access": True,
    "region": "us-east-1",
}


def _platform(events: list[tuple[str, str, object]]) -> PlatformApi:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        events.append((request.method, request.url.path, body))
        if request.method == "GET":
            return httpx.Response(200, json={"name": "iceberg", "storage_config": STORAGE})
        return httpx.Response(201, json={"name": NAME})

    return PlatformApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="http://api"))


def _polaris(events: list[tuple[str, str, object]]) -> PolarisClient:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "token"})
        body = json.loads(request.content) if request.content else None
        events.append((request.method, request.url.path, body))
        return httpx.Response(201 if request.method in ("POST", "PUT") else 404, json={})

    return PolarisClient(
        httpx.Client(transport=httpx.MockTransport(handle)),
        catalog_uri="http://polaris/api/catalog",
        management_uri="http://polaris/api/management/v1",
        credential="e2e-id:e2e-secret",
        scope="PRINCIPAL_ROLE:ALL",
    )


def _create(tmp_path, events: list[tuple[str, str, object]], cleanup: CleanupStack) -> OwnedCatalog:
    loaded: list[str] = []

    def load(warehouse: str) -> Catalog:
        loaded.append(warehouse)
        return cast(Catalog, object())

    owned = OwnedCatalog.create(
        platform=_platform(events),
        polaris=_polaris(events),
        s3=fs.SubTreeFileSystem(str(tmp_path), fs.LocalFileSystem()),
        cleanup=cleanup,
        platform_catalog="iceberg",
        name=NAME,
        load_iceberg=load,
    )
    assert loaded == [NAME]
    return owned


def test_the_catalog_is_created_beside_the_platforms_storage_under_its_own_prefix(tmp_path):
    """It copies the platform catalog's storage settings but allows only its own prefix."""
    events: list[tuple[str, str, object]] = []
    owned = _create(tmp_path, events, CleanupStack())
    assert owned.name == NAME
    assert events == [
        ("GET", "/v1/catalogs/iceberg", None),
        (
            "POST",
            "/v1/catalogs",
            {
                "name": NAME,
                "type": "INTERNAL",
                "default_base_location": f"s3://tm-e2e-catalogs/{NAME}",
                "storage_config": {
                    "storage_type": "S3",
                    "allowed_locations": [f"s3://tm-e2e-catalogs/{NAME}"],
                    "endpoint": "http://rustfs:9000",
                    "sts_endpoint": "http://rustfs:9000",
                    "path_style_access": True,
                },
            },
        ),
    ]
    assert (tmp_path / "tm-e2e-catalogs").is_dir()


def test_its_undo_drops_the_catalog_then_removes_its_prefix(tmp_path):
    """The catalog goes first (its grants restored by drop_catalog), then the storage it wrote."""
    events: list[tuple[str, str, object]] = []
    cleanup = CleanupStack()
    _create(tmp_path, events, cleanup)
    (tmp_path / "tm-e2e-catalogs" / NAME / "ns").mkdir(parents=True)
    events.clear()
    assert cleanup.run() == []
    assert events == [("GET", f"/api/management/v1/catalogs/{NAME}", None)]
    assert not (tmp_path / "tm-e2e-catalogs" / NAME).exists()


def test_revoking_reads_takes_only_the_content_grants_from_catalog_admin(tmp_path):
    """CATALOG_MANAGE_ACCESS stays, so the grants can be given back."""
    events: list[tuple[str, str, object]] = []
    owned = _create(tmp_path, events, CleanupStack())
    events.clear()
    owned.revoke_reads(_polaris(events))
    grants = f"/api/management/v1/catalogs/{NAME}/catalog-roles/catalog_admin/grants"
    assert events == [
        ("POST", grants, {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}),
        ("POST", grants, {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_METADATA"}}),
    ]


def test_restoring_reads_grants_back_what_revoking_took(tmp_path):
    """The same two privileges go back on ``catalog_admin``, so a scenario can make the catalog readable again."""
    events: list[tuple[str, str, object]] = []
    owned = _create(tmp_path, events, CleanupStack())
    events.clear()
    owned.restore_reads(_polaris(events))
    grants = f"/api/management/v1/catalogs/{NAME}/catalog-roles/catalog_admin/grants"
    assert events == [
        ("PUT", grants, {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}),
        ("PUT", grants, {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_METADATA"}}),
    ]
