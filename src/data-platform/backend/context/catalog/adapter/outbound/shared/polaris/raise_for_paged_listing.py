"""Define the raise_for_paged_listing function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.exceptions import CatalogUnavailableError

if TYPE_CHECKING:
    from collections.abc import Mapping

_NEXT_PAGE_TOKEN = "next-page-token"  # noqa: S105


def raise_for_paged_listing(body: Mapping[str, Any]) -> None:
    """Raise CatalogUnavailableError when an Iceberg REST list response says more pages follow.

    Listings are read in one request, so a ``next-page-token`` means the result would be cut
    short. Failing loudly keeps the API from disagreeing with Polaris without saying so.
    """
    if body.get(_NEXT_PAGE_TOKEN) is not None:
        raise CatalogUnavailableError("Polaris returned a paged listing, which is not supported yet")
