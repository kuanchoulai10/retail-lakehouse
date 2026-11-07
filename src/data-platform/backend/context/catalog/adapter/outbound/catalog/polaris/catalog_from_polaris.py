"""Define the catalog_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.catalog.polaris.catalog_from_polaris_object import (
    catalog_from_polaris_object,
)
from context.catalog.adapter.outbound.shared.polaris import read_polaris_reply

if TYPE_CHECKING:
    import httpx

    from context.catalog.application.port.outbound.catalog import Catalog


def catalog_from_polaris(response: httpx.Response, name: str) -> Catalog:
    """Map a Polaris management API reply holding one catalog to the Catalog aggregate.

    ``name`` names the catalog asked for. A reply that is not a JSON object, lacks a required
    field, or holds a value this backend does not understand, such as an unknown catalog,
    storage, connection or authentication type, raises CatalogUnavailableError naming the
    catalog, so the API answers 502 rather than 500.
    """
    return read_polaris_reply(response, f"catalog {name}", catalog_from_polaris_object)
