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
    """Every field of the catalog web use cases is populated."""
    web = build_catalog_web_use_cases(PolarisStub().client())

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


def test_read_never_echoes_a_connection_secret_even_if_polaris_returns_one():
    """Polaris treats connection secrets as input-only; should a read carry one, our API still drops it."""
    external = {
        **SALES,
        "type": "EXTERNAL",
        "connectionConfigInfo": {
            "connectionType": "ICEBERG_REST",
            "uri": "https://remote.example/api/catalog",
            "authenticationParameters": {"authenticationType": "BEARER", "bearerToken": "leaked-token"},
        },
    }
    stub = PolarisStub()
    stub.on("GET", f"{CATALOGS}/sales", httpx.Response(200, json=external))
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.get("/v1/catalogs/sales")

    assert response.status_code == 200
    assert response.json()["connection_config"]["connection_type"] == "REST"
    assert response.json()["connection_config"]["authentication"]["authentication_type"] == "BEARER"
    assert "leaked-token" not in response.text


def test_namespace_with_dot_part_is_served_end_to_end_against_polaris():
    """A dotted part is one part in the Polaris create body and in the read path."""
    stub = PolarisStub()
    stub.on(
        "POST", "/api/catalog/v1/sales/namespaces", httpx.Response(200, json={"namespace": ["a.b"], "properties": {}})
    )
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces/a.b",
        httpx.Response(200, json={"namespace": ["a.b"], "properties": {"k": "v"}}),
    )
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    created = client.post("/v1/catalogs/sales/namespaces", json={"namespace": ["a.b"]})
    fetched = client.get("/v1/catalogs/sales/namespaces/a.b")

    assert created.status_code == 201
    assert created.json()["namespace"] == ["a.b"]
    assert fetched.json() == {"catalog": "sales", "namespace": ["a.b"], "properties": {"k": "v"}}


def test_replaced_table_properties_save_is_a_409_reload_end_to_end():
    """Polaris's 409 on the uuid requirement reaches the user as 409 with the reload message."""
    stub = PolarisStub()
    stub.on(
        "POST",
        "/api/catalog/v1/sales/namespaces/retail/tables/orders",
        httpx.Response(409, json={"error": {"message": "Requirement failed: UUID does not match", "code": 409}}),
    )
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.put(
        "/v1/catalogs/sales/namespaces/retail/tables/orders/properties",
        json={"expected_uuid": "old-uuid", "updates": {"tier": "gold"}},
    )

    assert (response.status_code, response.json()) == (
        409,
        {"detail": "table orders changed since you loaded it, reload"},
    )
    (request,) = stub.requests
    assert request.content and b'"assert-table-uuid"' in request.content


def test_unreadable_table_metadata_is_a_502_end_to_end():
    """Table metadata the backend cannot read answers 502 with a message, never a 500."""
    stub = PolarisStub()
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces/retail/tables/orders",
        httpx.Response(200, json={"metadata": {"format-version": 2}}),
    )
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.get("/v1/catalogs/sales/namespaces/retail/tables/orders")

    assert response.status_code == 502
    assert "table orders in a form this backend cannot read" in response.json()["detail"]


def test_view_and_generic_table_are_served_end_to_end_against_polaris():
    """A view is created and read through Iceberg REST; a generic table through the Polaris API prefix."""
    stub = PolarisStub()
    view_body = {
        "metadata": {
            "view-uuid": "vu-1",
            "format-version": 1,
            "location": "s3://w/v",
            "current-version-id": 1,
            "versions": [
                {
                    "version-id": 1,
                    "timestamp-ms": 5,
                    "schema-id": 0,
                    "summary": {},
                    "representations": [{"type": "sql", "sql": "SELECT 1", "dialect": "spark"}],
                    "default-namespace": ["retail"],
                }
            ],
            "schemas": [{"type": "struct", "schema-id": 0, "fields": []}],
        }
    }
    stub.on("POST", "/api/catalog/v1/sales/namespaces/retail/views", httpx.Response(200, json=view_body))
    stub.on(
        "POST",
        "/api/catalog/polaris/v1/sales/namespaces/retail/generic-tables",
        httpx.Response(200, json={"table": {"name": "events", "format": "delta"}}),
    )
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    view = client.post(
        "/v1/catalogs/sales/namespaces/retail/views", json={"name": "v", "sql": "SELECT 1", "dialect": "spark"}
    )
    table = client.post(
        "/v1/catalogs/sales/namespaces/retail/generic-tables", json={"name": "events", "format": "delta"}
    )

    assert (view.status_code, view.json()["sql"], view.json()["uuid"]) == (201, "SELECT 1", "vu-1")
    assert (table.status_code, table.json()["format"]) == (201, "delta")


def test_unreadable_view_is_a_502_end_to_end():
    """A view whose current version matches no version answers 502 with a message, never a 500."""
    stub = PolarisStub()
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces/retail/views/v",
        httpx.Response(
            200,
            json={
                "metadata": {
                    "view-uuid": "vu-1",
                    "location": "s3://w/v",
                    "current-version-id": 9,
                    "versions": [],
                    "schemas": [],
                }
            },
        ),
    )
    client = TestClient(create_api_app(lambda app: register_routes(app, build_catalog_web_use_cases(stub.client()))))

    response = client.get("/v1/catalogs/sales/namespaces/retail/views/v")

    assert response.status_code == 502
    assert "view v in a form this backend cannot read" in response.json()["detail"]
