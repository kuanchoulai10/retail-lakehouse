"""Test the catalog use cases against the in-memory repo and the recording grant gateway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from context.catalog.application.port.inbound.catalog import (
    CreateCatalogUseCaseInput,
    DeleteCatalogUseCaseInput,
    GetCatalogUseCaseInput,
    ListCatalogsUseCaseInput,
    UpdateCatalogUseCaseInput,
)
from context.catalog.application.port.outbound.catalog import (
    CatalogId,
    CreateCatalogContentGrantGatewayInput,
)
from context.catalog.application.service.catalog import (
    CreateCatalogService,
    DeleteCatalogService,
    GetCatalogService,
    ListCatalogsService,
    UpdateCatalogService,
)
from tests.context.catalog.fakes.recording_create_catalog_content_grant_gateway import (
    RecordingCreateCatalogContentGrantGateway,
)

if TYPE_CHECKING:
    from tests.context.catalog.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo

S3: dict[str, Any] = {
    "storage_type": "S3",
    "allowed_locations": ["s3://bucket/"],
    "endpoint": "http://rustfs:9000",
    "path_style_access": True,
}


def _create_input(name: str = "sales", **overrides: Any) -> CreateCatalogUseCaseInput:  # noqa: ANN401
    fields: dict[str, Any] = {
        "name": name,
        "type": "INTERNAL",
        "default_base_location": f"s3://bucket/{name}",
        "storage_config": S3,
    }
    fields.update(overrides)
    return CreateCatalogUseCaseInput(**fields)


def _create(repo: InMemoryCatalogsRepo, name: str = "sales") -> None:
    CreateCatalogService(repo, RecordingCreateCatalogContentGrantGateway()).execute(_create_input(name))


def _update_input(entity_version: int, **overrides: Any) -> UpdateCatalogUseCaseInput:  # noqa: ANN401
    fields: dict[str, Any] = {
        "name": "sales",
        "entity_version": entity_version,
        "default_base_location": "s3://bucket/sales-v2",
        "properties": {"owner": "data-team"},
        "storage_config": S3,
    }
    fields.update(overrides)
    return UpdateCatalogUseCaseInput(**fields)


def test_create_catalog_grants_content_to_catalog_admin(catalogs_repo, content_grant_gateway):
    """Creating a catalog saves it, then grants content rights to that catalog's own admin role."""
    output = CreateCatalogService(catalogs_repo, content_grant_gateway).execute(_create_input())

    assert content_grant_gateway.calls == [CreateCatalogContentGrantGatewayInput(catalog_name="sales")]
    assert output.name == "sales"
    assert output.type == "INTERNAL"
    assert output.default_base_location == "s3://bucket/sales"
    assert output.properties == {"default-base-location": "s3://bucket/sales"}
    assert output.storage_config["storage_type"] == "S3"
    assert output.storage_config["allowed_locations"] == ["s3://bucket/"]
    assert output.storage_config["path_style_access"] is True
    assert output.entity_version == 1
    assert catalogs_repo.get(CatalogId.of("sales")) is not None


@pytest.mark.parametrize(
    "error",
    [
        PermissionDeniedError("Principal 'root' is not authorized for op ADD_CATALOG_GRANT_TO_CATALOG_ROLE"),
        CatalogUnavailableError("Polaris is unreachable: connection reset"),
        NotFoundError("CatalogRole not found: catalog_admin"),
    ],
)
def test_create_catalog_reports_grant_failure_without_claiming_success(catalogs_repo, error: Exception):
    """A failed grant is reported with Polaris's message, and the created catalog is left in place."""
    service = CreateCatalogService(catalogs_repo, RecordingCreateCatalogContentGrantGateway(error=error))

    with pytest.raises(type(error)) as raised:
        service.execute(_create_input())

    assert str(raised.value) == f"catalog sales was created but the content grant failed: {error}"
    assert raised.value.__cause__ is error
    assert catalogs_repo.get(CatalogId.of("sales")) is not None


def test_create_catalog_with_taken_name_does_not_grant(catalogs_repo, content_grant_gateway):
    """A catalog that already exists is a conflict, and nothing is granted."""
    _create(catalogs_repo)

    with pytest.raises(ConflictError, match="already exists"):
        CreateCatalogService(catalogs_repo, content_grant_gateway).execute(_create_input())

    assert content_grant_gateway.calls == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "  "}, "catalog name must not be blank"),
        ({"default_base_location": ""}, "default base location must not be blank"),
        ({"type": "FEDERATED"}, "catalog type must be one of INTERNAL, EXTERNAL"),
        ({"storage_config": {"allowed_locations": []}}, "storage_type is required"),
        ({"storage_config": {"storage_type": "S3", "bucket": "b"}}, "unknown storage config field"),
    ],
)
def test_create_catalog_rejects_invalid_input(catalogs_repo, content_grant_gateway, overrides, message):
    """Invalid input is a validation error and creates nothing."""
    with pytest.raises(ValidationError, match=message):
        CreateCatalogService(catalogs_repo, content_grant_gateway).execute(_create_input(**overrides))

    assert catalogs_repo.items == {}
    assert content_grant_gateway.calls == []


def test_update_catalog_sends_the_version_the_caller_loaded(catalogs_repo):
    """An update replaces the properties, keeps the base location property and bumps the version."""
    _create(catalogs_repo)

    output = UpdateCatalogService(catalogs_repo).execute(_update_input(entity_version=1))

    assert output.entity_version == 2
    assert output.properties == {"owner": "data-team", "default-base-location": "s3://bucket/sales-v2"}
    assert output.default_base_location == "s3://bucket/sales-v2"


def test_update_catalog_conflict_says_reload(catalogs_repo):
    """Saving over a newer version reports that the catalog changed and must be reloaded."""
    _create(catalogs_repo)
    UpdateCatalogService(catalogs_repo).execute(_update_input(entity_version=1))

    with pytest.raises(ConflictError) as raised:
        UpdateCatalogService(catalogs_repo).execute(_update_input(entity_version=1))

    assert str(raised.value) == "catalog sales changed since you loaded it, reload"
    assert catalogs_repo.items["sales"].entity_version == 2


def test_update_unknown_catalog_is_not_found(catalogs_repo):
    """Updating a catalog that does not exist is a not-found."""
    with pytest.raises(NotFoundError, match="catalog sales not found"):
        UpdateCatalogService(catalogs_repo).execute(_update_input(entity_version=1))


def test_update_catalog_rejects_blank_base_location(catalogs_repo):
    """An update must keep a default base location."""
    _create(catalogs_repo)

    with pytest.raises(ValidationError, match="default base location must not be blank"):
        UpdateCatalogService(catalogs_repo).execute(_update_input(entity_version=1, default_base_location=" "))


def test_get_catalog_returns_it(catalogs_repo):
    """Getting a catalog returns its fields."""
    _create(catalogs_repo)

    output = GetCatalogService(catalogs_repo).execute(GetCatalogUseCaseInput(name="sales"))

    assert (output.name, output.entity_version) == ("sales", 1)


def test_get_unknown_catalog_is_not_found(catalogs_repo):
    """Getting a catalog that does not exist is a not-found."""
    with pytest.raises(NotFoundError, match="catalog nope not found"):
        GetCatalogService(catalogs_repo).execute(GetCatalogUseCaseInput(name="nope"))


def test_delete_catalog_removes_it(catalogs_repo):
    """Deleting a catalog removes it."""
    _create(catalogs_repo)

    DeleteCatalogService(catalogs_repo).execute(DeleteCatalogUseCaseInput(name="sales"))

    assert catalogs_repo.items == {}


def test_delete_unknown_catalog_is_not_found(catalogs_repo):
    """Deleting a catalog that does not exist is a not-found."""
    with pytest.raises(NotFoundError, match="catalog nope not found"):
        DeleteCatalogService(catalogs_repo).execute(DeleteCatalogUseCaseInput(name="nope"))


def test_list_catalogs_returns_every_catalog(catalogs_repo):
    """Listing returns every catalog."""
    _create(catalogs_repo, "sales")
    _create(catalogs_repo, "iceberg")

    output = ListCatalogsService(catalogs_repo).execute(ListCatalogsUseCaseInput())

    assert [item.name for item in output.items] == ["iceberg", "sales"]
