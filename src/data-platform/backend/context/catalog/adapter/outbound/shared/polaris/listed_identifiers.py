"""Define the listed_identifiers function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.shared.polaris.raise_for_paged_listing import (
    raise_for_paged_listing,
)
from context.catalog.application.exceptions import CatalogUnavailableError

if TYPE_CHECKING:
    import httpx


def listed_identifiers(response: httpx.Response, description: str) -> list[tuple[tuple[str, ...], str]]:
    """Return ``(namespace parts, name)`` for each identifier of a table, view or generic table listing.

    ``description`` names what was listed (``the views of namespace ['a']``). A reply that is
    not JSON or holds an identifier without a namespace list and a name raises
    CatalogUnavailableError; a paged listing raises it too (Ruling R8), so nothing is cut short.
    """
    try:
        body = response.json()
        identifiers = body.get("identifiers", [])
        found = []
        for item in identifiers:
            namespace, name = item["namespace"], item["name"]
            if not isinstance(namespace, list) or not isinstance(name, str):
                raise TypeError(f"identifier {item!r} needs a namespace list and a name")
            found.append((tuple(str(part) for part in namespace), name))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise CatalogUnavailableError(
            f"Polaris returned {description} in a form this backend cannot read: {exc!r}"
        ) from exc
    raise_for_paged_listing(body)
    return found
