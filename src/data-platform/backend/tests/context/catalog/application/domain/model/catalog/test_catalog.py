"""Test the Catalog aggregate on its Pydantic base."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from context.catalog.application.domain.model.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
    StorageConfig,
    StorageType,
)

S3 = StorageConfig(storage_type=StorageType.S3, allowed_locations=("s3://bucket/",))


def _catalog() -> Catalog:
    return Catalog.create(CatalogId.of("sales"), CatalogType.INTERNAL, "s3://bucket/sales", S3)


def test_create_sets_only_the_default_base_location():
    """A new catalog is unsaved, and its only property is its default base location."""
    catalog = _catalog()

    assert (catalog.name, catalog.entity_version, catalog.created_at) == ("sales", 0, None)
    assert catalog.properties == {"default-base-location": "s3://bucket/sales"}
    assert catalog.connection_config is None


def test_catalog_id_is_built_positionally_and_strict():
    """The id keeps its positional form and takes only a string."""
    assert CatalogId("sales") == CatalogId.of("sales")
    with pytest.raises(ValidationError):
        CatalogId(1)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "INTERNAL"),
        ("properties", {"a": 1}),
        ("storage_config", {"storage_type": "S3"}),
        ("entity_version", "1"),
        ("created_at", "2026-11-07T12:00:00Z"),
    ],
)
def test_assigning_a_wrong_type_is_rejected_and_changes_nothing(field: str, value: object):
    """Every assignment is validated strictly; a rejected one leaves the catalog as it was."""
    catalog = _catalog()
    before = catalog.model_dump()

    with pytest.raises(ValidationError):
        setattr(catalog, field, value)

    assert catalog.model_dump() == before


def test_reconfigure_replaces_properties_storage_and_version():
    """``default_base_location`` wins over a property of the same name."""
    catalog = _catalog()
    gcs = StorageConfig(storage_type=StorageType.GCS)

    catalog.reconfigure(
        default_base_location="s3://bucket/v2",
        properties={"owner": "data", "default-base-location": "ignored"},
        storage_config=gcs,
        loaded_version=3,
    )

    assert catalog.properties == {"owner": "data", "default-base-location": "s3://bucket/v2"}
    assert (catalog.storage_config, catalog.entity_version) == (gcs, 3)


def test_rejected_reconfigure_changes_nothing():
    """A reconfigure with one invalid input leaves every field as it was."""
    catalog = _catalog()
    before = catalog.model_dump()

    with pytest.raises(ValidationError):
        catalog.reconfigure(
            default_base_location="s3://bucket/v2",
            properties={"owner": "data"},
            storage_config=S3,
            loaded_version="3",  # ty: ignore[invalid-argument-type]
        )

    assert catalog.model_dump() == before


def test_catalogs_are_equal_by_id():
    """Two catalogs with one name are one catalog, whatever their other fields."""
    later = _catalog()
    later.updated_at = datetime(2026, 11, 7, tzinfo=UTC)

    assert later == _catalog()
