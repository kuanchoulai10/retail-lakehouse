"""Test that the catalog web use cases are wired to Polaris and served end to end."""

from __future__ import annotations

from dataclasses import fields

import httpx
from fastapi.testclient import TestClient

from bootstrap.container import build_catalog_web_use_cases, create_api_app
from context.catalog.adapter.inbound.web import register_routes
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import (
    PolarisStub,
)

CATALOGS = "/api/management/v1/catalogs"
SALES: dict[str, object] = {
    "type": "INTERNAL",
    "name": "sales",
    "properties": {"default-base-location": "s3://bucket/sales"},
    "entityVersion": 1,
    "storageConfigInfo": {"storageType": "S3", "allowedLocations": ["s3://bucket/"]},
}


def test_every_catalog_web_use_case_is_populated():
    """All five catalog web use case fields are set."""
    web = build_catalog_web_use_cases(PolarisStub().client())

    assert len(fields(web)) == 5
    assert all(getattr(web, f.name) is not None for f in fields(web))


def test_create_catalog_is_served_end_to_end_against_polaris():
    """Creating a catalog through the API creates it in Polaris, then grants its content privilege."""
    stub = PolarisStub()
    stub.on("POST", CATALOGS, httpx.Response(201, json=SALES))
    stub.on("PUT", f"{CATALOGS}/sales/catalog-roles/catalog_admin/grants", httpx.Response(201))
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.post(
        "/v1/catalogs",
        json={
            "name": "sales",
            "type": "INTERNAL",
            "default_base_location": "s3://bucket/sales",
            "storage_config": {"storage_type": "S3", "allowed_locations": ["s3://bucket/"]},
        },
    )

    assert response.status_code == 201
    assert [(r.method, r.url.path) for r in stub.requests] == [
        ("POST", CATALOGS),
        ("PUT", f"{CATALOGS}/sales/catalog-roles/catalog_admin/grants"),
    ]


def test_unreachable_polaris_is_a_502():
    """A Polaris that cannot be reached answers 502 with a message."""
    stub = PolarisStub()
    stub.fail_token(httpx.ConnectError("connection refused"))
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.get("/v1/catalogs")

    assert response.status_code == 502
    assert "connection refused" in response.json()["detail"]
