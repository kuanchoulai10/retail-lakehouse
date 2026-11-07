"""Define the listed_catalog_names function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris.read_polaris_reply import read_polaris_reply

if TYPE_CHECKING:
    import httpx


def _names(body: dict[str, Any]) -> list[str]:
    names = []
    for catalog in body["catalogs"]:
        name = catalog["name"]
        if not isinstance(name, str):
            raise TypeError(f"catalog name must be a string, not {name!r}")
        names.append(name)
    return names


def listed_catalog_names(response: httpx.Response) -> list[str]:
    """Return the name of each catalog of a Polaris management ListCatalogsResponse.

    A reply without a ``catalogs`` list of named catalog objects raises CatalogUnavailableError.
    """
    return read_polaris_reply(response, "the catalog list", _names)
