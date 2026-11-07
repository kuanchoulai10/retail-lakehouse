"""Define the read_polaris_reply function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.exceptions import CatalogUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

_UNREADABLE = (AttributeError, KeyError, TypeError, ValueError)


def read_polaris_reply[T](response: httpx.Response, description: str, read: Callable[[dict[str, Any]], T]) -> T:
    """Decode a Polaris reply as a JSON object and map it with ``read``, or raise CatalogUnavailableError.

    A reply that is not JSON, is JSON but not an object, or holds a shape ``read`` cannot map
    (it raises AttributeError, KeyError, TypeError or ValueError) is an upstream fault: it
    raises CatalogUnavailableError naming ``description`` (``table orders``), so the API
    answers 502 rather than 500. Every Polaris mapper reads its reply through here.
    """
    try:
        body = response.json()
        if not isinstance(body, dict):
            raise TypeError(f"expected a JSON object, not {type(body).__name__}")
        return read(body)
    except _UNREADABLE as exc:
        raise CatalogUnavailableError(
            f"Polaris returned {description} in a form this backend cannot read: {exc!r}"
        ) from exc
