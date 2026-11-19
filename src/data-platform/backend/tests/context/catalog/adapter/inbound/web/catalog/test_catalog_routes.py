"""Test the catalog routes."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from context.catalog.adapter.inbound.web.catalog import AuthenticationParametersApiRequest
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
    UpdateCatalogUseCaseInput,
    UpdateCatalogUseCaseOutput,
)
from context.catalog.application.service.catalog import CreateCatalogService
from tests.context.catalog.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_app,
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


class _ServiceBuildingABadOutput(StubUseCase):
    """A list catalogs service with a bug: it builds its output with a list where a tuple is declared."""

    def execute(self, request: Any) -> Any:  # noqa: ANN401
        """Record the request, then build the refused output."""
        self.requests.append(request)
        return ListCatalogsUseCaseOutput(items=[])  # ty: ignore[invalid-argument-type]


def test_an_output_the_service_cannot_build_answers_500_not_422():
    """A refused output is a server bug: the route answers 500, never a client error."""
    client = TestClient(build_app(list_catalogs=_ServiceBuildingABadOutput()), raise_server_exceptions=False)

    response = client.get("/v1/catalogs")

    assert response.status_code == 500


def test_an_output_the_service_cannot_build_reaches_the_server_unhandled():
    """No handler takes the refused output's TypeError, so the server logs it with its traceback."""
    client = TestClient(build_app(list_catalogs=_ServiceBuildingABadOutput()))

    with pytest.raises(TypeError, match="ListCatalogsUseCaseOutput was built with refused data: items"):
        client.get("/v1/catalogs")


def test_list_catalogs():
    """Listing returns every catalog."""
    output = ListCatalogsUseCaseOutput(items=(ListCatalogsUseCaseOutput.Catalog(**FIELDS),))
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
    assert response.json() == {"detail": "connection_config.authentication.authentication_type: Field required"}


def test_external_catalog_without_authentication_returns_422():
    """The connection's authentication is required on create, though a catalog may be read back without it."""
    body = {**EXTERNAL_BODY, "connection_config": {"connection_type": "HIVE", "uri": "thrift://h"}}

    response = _real_create_client().post("/v1/catalogs", json=body)

    assert response.status_code == 422
    assert response.json() == {"detail": "connection_config.authentication: Field required"}


EXTERNAL_RESPONSE_TEXT = (
    '{"name":"sales","type":"EXTERNAL","default_base_location":"s3://bucket/sales",'
    '"properties":{"default-base-location":"s3://bucket/sales"},'
    '"storage_config":{"storage_type":"S3","allowed_locations":["s3://bucket/"],"region":null,"role_arn":null,'
    '"external_id":null,"user_arn":null,"endpoint":"http://rustfs:9000","endpoint_internal":null,'
    '"sts_endpoint":null,"sts_unavailable":null,"path_style_access":true,"tenant_id":null,'
    '"multi_tenant_app_name":null,"consent_url":null,"gcs_service_account":null},'
    '"connection_config":{"connection_type":"REST","uri":"https://remote.example/api/catalog",'
    '"authentication":{"authentication_type":"OAUTH","token_uri":"https://remote.example/oauth/tokens",'
    '"client_id":"remote-client","scopes":["PRINCIPAL_ROLE:ALL"],"role_arn":null,"role_session_name":null,'
    '"external_id":null,"signing_region":null,"signing_name":null}},'
    '"entity_version":1,"created_at":"2026-11-07T12:00:00Z","updated_at":"2026-11-07T12:00:00Z"}'
)


def test_created_external_catalog_body_is_unchanged():
    """The created external catalog is described byte for byte as before the domain moved to Pydantic."""
    response = _real_create_client().post("/v1/catalogs", json=EXTERNAL_BODY)

    assert response.status_code == 201
    assert response.text == EXTERNAL_RESPONSE_TEXT


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


def test_invalid_catalog_name_answers_422_with_the_reason():
    """A catalog name that breaks the id's invariant answers 422 with a one-line reason."""
    response = _real_create_client().post("/v1/catalogs", json={**CREATE_BODY, "name": "sa\x1fles"})

    assert (response.status_code, response.json()) == (
        422,
        {"detail": "catalog name must not contain the unit separator U+001F"},
    )


def test_storage_invariant_answers_422_with_the_dotted_field():
    """A storage config that breaks a field rule answers 422 naming the field under storage_config."""
    body = {**CREATE_BODY, "storage_config": {"storage_type": "AZURE"}}

    response = _real_create_client().post("/v1/catalogs", json=body)

    assert (response.status_code, response.json()) == (
        422,
        {"detail": "storage_config.tenant_id: required for AZURE storage"},
    )


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


def test_authentication_request_repr_leaves_out_the_secrets():
    """The request DTO carries the secrets in; printing it must not show them."""
    request = AuthenticationParametersApiRequest(
        authentication_type="OAUTH", client_secret="oauth-s3cr3t", bearer_token="bearer-t0ken"
    )

    assert "oauth-s3cr3t" not in repr(request)
    assert "bearer-t0ken" not in repr(request)
