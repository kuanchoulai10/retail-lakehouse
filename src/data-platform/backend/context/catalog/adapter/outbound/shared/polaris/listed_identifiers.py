"""Define the listed_identifiers function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris.namespace_parts_from_polaris import (
    namespace_parts_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.raise_for_paged_listing import (
    raise_for_paged_listing,
)
from context.catalog.adapter.outbound.shared.polaris.read_polaris_reply import read_polaris_reply

if TYPE_CHECKING:
    import httpx


def _identifiers(body: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[tuple[str, ...], str]]]:
    found = []
    for item in body.get("identifiers", []):
        namespace, name = item["namespace"], item["name"]
        if not isinstance(namespace, list) or not isinstance(name, str):
            raise TypeError(f"identifier {item!r} needs a namespace list and a name")
        found.append((namespace_parts_from_polaris(namespace), name))
    return body, found


def listed_identifiers(response: httpx.Response, description: str) -> list[tuple[tuple[str, ...], str]]:
    """Return ``(namespace parts, name)`` for each identifier of a table, view or generic table listing.

    ``description`` names what was listed (``the views of namespace ['a']``). A reply that is
    not JSON or holds an identifier without a namespace list of strings and a name raises
    CatalogUnavailableError; a paged listing raises it too (Ruling R8), so nothing is cut short.
    """
    body, found = read_polaris_reply(response, description, _identifiers)
    raise_for_paged_listing(body)
    return found
