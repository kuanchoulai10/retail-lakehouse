"""Test the lazy, caching Iceberg catalog factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pydantic import SecretStr

from bootstrap.configs import CatalogSettings
from bootstrap.container import build_catalog_factory

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog


class RecordingLoader:
    """Catalog loader stub that records its calls."""

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, name: str, **properties: Any) -> Catalog:  # noqa: ANN401
        """Record the catalog name and properties and return a placeholder catalog."""
        self.calls.append((name, properties))
        return cast("Catalog", object())


def test_factory_loads_a_rest_catalog_per_name_lazily_and_caches_it():
    """The factory loads a catalog only on first use per name and returns the cached one afterwards."""
    loader = RecordingLoader()
    settings = CatalogSettings(
        uri="http://polaris:8181/api/catalog",
        credential=SecretStr("root:secret"),
        s3_endpoint="http://rustfs:9000",
    )

    factory = build_catalog_factory(settings, loader=loader)
    assert loader.calls == []

    first = factory("iceberg")
    assert factory("iceberg") is first
    factory("other")

    assert [name for name, _ in loader.calls] == ["iceberg", "other"]
    assert loader.calls[0][1] == {
        "type": "rest",
        "uri": "http://polaris:8181/api/catalog",
        "credential": "root:secret",
        "warehouse": "iceberg",
        "scope": "PRINCIPAL_ROLE:ALL",
        "s3.endpoint": "http://rustfs:9000",
        "s3.path-style-access": "true",
        "s3.region": "dummy-region",
    }


def test_factory_passes_s3_keys_when_set():
    """The S3 access and secret keys are passed to the catalog when configured."""
    loader = RecordingLoader()
    settings = CatalogSettings(s3_access_key_id=SecretStr("AKID"), s3_secret_access_key=SecretStr("SK"))

    build_catalog_factory(settings, loader=loader)("iceberg")

    properties = loader.calls[0][1]
    assert properties["s3.access-key-id"] == "AKID"
    assert properties["s3.secret-access-key"] == "SK"
