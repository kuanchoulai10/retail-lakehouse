"""Define the catalogs_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.catalog.polaris.catalog_from_polaris_object import (
    catalog_from_polaris_object,
)
from context.catalog.adapter.outbound.shared.polaris import read_polaris_reply

if TYPE_CHECKING:
    import httpx

    from context.catalog.application.port.outbound.catalog import Catalog


def _catalogs(body: dict[str, Any]) -> list[Catalog]:
    listed = body["catalogs"]
    if not isinstance(listed, list):
        raise TypeError(f"catalogs must be a list, not {listed!r}")
    return [catalog_from_polaris_object(item) for item in listed]


def catalogs_from_polaris(response: httpx.Response) -> list[Catalog]:
    """Map a Polaris management API ListCatalogsResponse to Catalog aggregates.

    A reply without a ``catalogs`` list, or with an item ``catalog_from_polaris_object``
    cannot read, raises CatalogUnavailableError, so the API answers 502 rather than 500.
    """
    return read_polaris_reply(response, "the catalog list", _catalogs)
