"""Provide the build_catalog_factory function."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from pyiceberg.catalog import load_catalog

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyiceberg.catalog import Catalog

    from bootstrap.configs import CatalogSettings


def _properties(settings: CatalogSettings, name: str) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "type": "rest",
        "uri": settings.uri,
        "credential": settings.credential.get_secret_value(),
        "warehouse": name,
        "scope": settings.scope,
        "s3.endpoint": settings.s3_endpoint,
        "s3.path-style-access": str(settings.s3_path_style_access).lower(),
        "s3.region": settings.s3_region,
    }
    if settings.s3_access_key_id is not None:
        properties["s3.access-key-id"] = settings.s3_access_key_id.get_secret_value()
    if settings.s3_secret_access_key is not None:
        properties["s3.secret-access-key"] = (
            settings.s3_secret_access_key.get_secret_value()
        )
    return properties


def build_catalog_factory(
    settings: CatalogSettings,
    *,
    loader: Callable[..., Catalog] = load_catalog,
) -> Callable[[str], Catalog]:
    """Return a factory that loads each Polaris catalog on first use, then reuses it.

    Loading talks to Polaris, so it is deferred to the first call for a name.
    """
    catalogs: dict[str, Catalog] = {}
    lock = threading.Lock()

    def factory(name: str) -> Catalog:
        with lock:
            catalog = catalogs.get(name)
            if catalog is None:
                catalog = loader(name, **_properties(settings, name))
                catalogs[name] = catalog
            return catalog

    return factory
