"""Test the catalog routes."""

from __future__ import annotations

from typing import Any

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    PermissionDeniedError,
)
from context.catalog.application.port.inbound.catalog import (
    CreateCatalogUseCaseInput,
    CreateCatalogUseCaseOutput,
    DeleteCatalogUseCaseInput,
    DeleteCatalogUseCaseOutput,
    GetCatalogUseCaseInput,
    GetCatalogUseCaseOutput,
    ListCatalogsUseCaseOutput,
    ListCatalogsUseCaseOutputItem,
    UpdateCatalogUseCaseInput,
    UpdateCatalogUseCaseOutput,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)

STORAGE: dict[str, Any] = {
    "storage_type": "S3",
    "allowed_locations": ["s3://bucket/"],
    "region": None,
    "role_arn": None,
    "external_id": None,
    "user_arn": None,
    "endpoint": "http://rustfs:9000",
    "endpoint_internal": None,
    "sts_endpoint": None,
    "sts_unavailable": None,
    "path_style_access": True,
    "tenant_id": None,
    "multi_tenant_app_name": None,
    "consent_url": None,
    "gcs_service_account": None,
}
FIELDS: dict[str, Any] = {
    "name": "sales",
    "type": "INTERNAL",
    "default_base_location": "s3://bucket/sales",
    "properties": {"default-base-location": "s3://bucket/sales"},
    "storage_config": STORAGE,
    "entity_version": 1,
    "created_at": NOW,
    "updated_at": NOW,
}
UPDATED: dict[str, Any] = {**FIELDS, "entity_version": 2}
CREATE_BODY: dict[str, Any] = {
    "name": "sales",
    "type": "INTERNAL",
    "default_base_location": "s3://bucket/sales",
    "storage_config": {
        "storage_type": "S3",
        "allowed_locations": ["s3://bucket/"],
        "endpoint": "http://rustfs:9000",
        "path_style_access": True,
    },
}


def test_create_catalog_returns_201():
    """Creating a catalog returns 201 with the saved catalog and passes the form fields to the use case."""
    stub = StubUseCase(CreateCatalogUseCaseOutput(**FIELDS))
    client = build_client(create_catalog=stub)

    response = client.post("/v1/catalogs", json=CREATE_BODY)

    assert response.status_code == 201
    assert response.json()["name"] == "sales"
    assert response.json()["storage_config"] == STORAGE
    assert response.json()["entity_version"] == 1
    assert stub.requests == [
        CreateCatalogUseCaseInput(
            name="sales",
            type="INTERNAL",
            default_base_location="s3://bucket/sales",
            storage_config={
                "storage_type": "S3",
                "allowed_locations": ["s3://bucket/"],
                "endpoint": "http://rustfs:9000",
                "path_style_access": True,
            },
        )
    ]


def test_create_catalog_rejects_unknown_fields():
    """A body field the form does not have is rejected before the use case runs."""
    stub = StubUseCase(CreateCatalogUseCaseOutput(**FIELDS))
    client = build_client(create_catalog=stub)

    response = client.post("/v1/catalogs", json=CREATE_BODY | {"purge": True})

    assert response.status_code == 422
    assert stub.requests == []


def test_permission_denied_maps_to_403():
    """Polaris refusing the operation is a 403 that carries Polaris's message."""
    message = "catalog sales was created but the content grant failed: not authorized for op ADD_GRANT"
    client = build_client(create_catalog=StubUseCase(error=PermissionDeniedError(message)))

    response = client.post("/v1/catalogs", json=CREATE_BODY)

    assert response.status_code == 403
    assert response.json() == {"detail": message}


def test_unavailable_maps_to_502():
    """An unreachable Polaris is a 502 with a message."""
    message = "Polaris is unreachable: connection refused"
    client = build_client(list_catalogs=StubUseCase(error=CatalogUnavailableError(message)))

    response = client.get("/v1/catalogs")

    assert response.status_code == 502
    assert response.json() == {"detail": message}


def test_list_catalogs():
    """Listing returns every catalog."""
    output = ListCatalogsUseCaseOutput(items=[ListCatalogsUseCaseOutputItem(**FIELDS)])
    client = build_client(list_catalogs=StubUseCase(output))

    response = client.get("/v1/catalogs")

    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["sales"]


def test_get_catalog():
    """Getting a catalog passes its name to the use case."""
    stub = StubUseCase(GetCatalogUseCaseOutput(**FIELDS))
    client = build_client(get_catalog=stub)

    response = client.get("/v1/catalogs/sales")

    assert response.status_code == 200
    assert response.json()["default_base_location"] == "s3://bucket/sales"
    assert stub.requests == [GetCatalogUseCaseInput(name="sales")]


def test_update_catalog_passes_the_loaded_entity_version():
    """Updating a catalog passes the entity version the caller loaded, with the edit form's fields."""
    stub = StubUseCase(UpdateCatalogUseCaseOutput(**UPDATED))
    client = build_client(update_catalog=stub)

    response = client.put(
        "/v1/catalogs/sales",
        json={
            "entity_version": 1,
            "default_base_location": "s3://bucket/sales",
            "properties": {"owner": "data-team"},
            "storage_config": {"storage_type": "S3"},
        },
    )

    assert response.status_code == 200
    assert response.json()["entity_version"] == 2
    assert stub.requests == [
        UpdateCatalogUseCaseInput(
            name="sales",
            entity_version=1,
            default_base_location="s3://bucket/sales",
            properties={"owner": "data-team"},
            storage_config={"storage_type": "S3", "allowed_locations": []},
        )
    ]


def test_update_conflict_maps_to_409():
    """A stale update is a 409 that tells the caller to reload."""
    message = "catalog sales changed since you loaded it, reload"
    client = build_client(update_catalog=StubUseCase(error=ConflictError(message)))

    response = client.put(
        "/v1/catalogs/sales",
        json={"entity_version": 1, "default_base_location": "s3://b/", "storage_config": {"storage_type": "S3"}},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": message}


def test_delete_catalog_returns_204():
    """Deleting a catalog returns 204 and passes its name to the use case."""
    stub = StubUseCase(DeleteCatalogUseCaseOutput())
    client = build_client(delete_catalog=stub)

    response = client.delete("/v1/catalogs/sales")

    assert response.status_code == 204
    assert stub.requests == [DeleteCatalogUseCaseInput(name="sales")]
