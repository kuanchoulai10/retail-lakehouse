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
from context.catalog.application.service.catalog import CreateCatalogService
from tests.context.catalog.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)
from tests.context.catalog.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.catalog.fakes.recording_create_catalog_content_grant_gateway import (
    RecordingCreateCatalogContentGrantGateway,
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
    "connection_config": None,
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
        json={
            "entity_version": 1,
            "default_base_location": "s3://b/",
            "properties": {},
            "storage_config": {"storage_type": "S3"},
        },
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


OAUTH_CONNECTION: dict[str, Any] = {
    "connection_type": "REST",
    "uri": "https://remote.example/api/catalog",
    "authentication": {
        "authentication_type": "OAUTH",
        "token_uri": "https://remote.example/oauth/tokens",
        "client_id": "remote-client",
        "client_secret": "remote-s3cr3t",
        "scopes": ["PRINCIPAL_ROLE:ALL"],
    },
}
EXTERNAL_BODY: dict[str, Any] = {**CREATE_BODY, "type": "EXTERNAL", "connection_config": OAUTH_CONNECTION}


def _real_create_client():
    service = CreateCatalogService(InMemoryCatalogsRepo(), RecordingCreateCatalogContentGrantGateway())
    return build_client(create_catalog=service)


def test_create_external_catalog_passes_the_connection():
    """An external catalog's connection reaches the use case with only the fields that were given."""
    stub = StubUseCase(CreateCatalogUseCaseOutput(**FIELDS))
    client = build_client(create_catalog=stub)

    response = client.post("/v1/catalogs", json=EXTERNAL_BODY)

    assert response.status_code == 201
    (request,) = stub.requests
    assert request.connection_config == OAUTH_CONNECTION


def test_external_catalog_without_connection_returns_422():
    """An external catalog needs a connection; without one nothing is created."""
    response = _real_create_client().post("/v1/catalogs", json={**CREATE_BODY, "type": "EXTERNAL"})

    assert response.status_code == 422
    assert response.json() == {"detail": "an EXTERNAL catalog needs a connection_config"}


def test_external_catalog_without_authentication_type_returns_422():
    """The connection's authentication type is required, as in the upstream form."""
    body = {**EXTERNAL_BODY, "connection_config": {"connection_type": "HIVE", "authentication": {}}}

    response = _real_create_client().post("/v1/catalogs", json=body)

    assert response.status_code == 422


def test_response_never_contains_a_connection_secret():
    """The created catalog is described with its connection, and the client secret is not echoed back."""
    response = _real_create_client().post("/v1/catalogs", json=EXTERNAL_BODY)

    assert response.status_code == 201
    authentication = response.json()["connection_config"]["authentication"]
    assert authentication["client_id"] == "remote-client"
    assert "client_secret" not in authentication
    assert "bearer_token" not in authentication
    assert "remote-s3cr3t" not in response.text


def test_storage_user_arn_is_not_accepted():
    """The user ARN is assigned by Polaris, so a body that sets it is rejected."""
    body = {**CREATE_BODY, "storage_config": {"storage_type": "S3", "user_arn": "arn:aws:iam::1:user/x"}}

    response = _real_create_client().post("/v1/catalogs", json=body)

    assert response.status_code == 422


def test_update_without_properties_is_rejected():
    """Leaving the properties out must not wipe them, so the field is required."""
    stub = StubUseCase(UpdateCatalogUseCaseOutput(**UPDATED))
    client = build_client(update_catalog=stub)

    response = client.put(
        "/v1/catalogs/sales",
        json={"entity_version": 1, "default_base_location": "s3://b/", "storage_config": {"storage_type": "S3"}},
    )

    assert response.status_code == 422
    assert stub.requests == []
