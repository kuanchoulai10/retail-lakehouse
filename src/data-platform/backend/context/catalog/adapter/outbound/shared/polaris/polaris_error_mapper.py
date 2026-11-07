"""Define the raise_for_polaris function."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

if TYPE_CHECKING:
    import httpx

_ERROR_BY_STATUS: dict[int, type[Exception]] = {
    400: ValidationError,
    422: ValidationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
}
_FIRST_ERROR_STATUS = 400
_UNAUTHORIZED = 401


def _message(response: httpx.Response) -> str:
    """Return Polaris's ``error.message``, else the raw body, else the status line."""
    text = response.text
    try:
        body = json.loads(text)
    except ValueError:
        body = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return text or f"HTTP {response.status_code} {response.reason_phrase}"


def raise_for_polaris(response: httpx.Response) -> None:
    """Raise the application exception that matches a Polaris error response; pass any success.

    400 and 422 are a validation error, 403 permission denied, 404 not found, 409 a conflict,
    and any other status from 400 up means the catalog is unavailable. A 401 is unavailable
    too: every request carries the backend's own credential, so a rejected one is an upstream
    fault, not the caller's missing privilege. The exception message is Polaris's own
    ``{"error": {"message": ...}}`` when the body has one.
    """
    if response.status_code < _FIRST_ERROR_STATUS:
        return
    if response.status_code == _UNAUTHORIZED:
        raise CatalogUnavailableError(f"the catalog rejected the backend credential: {_message(response)}")
    error = _ERROR_BY_STATUS.get(response.status_code, CatalogUnavailableError)
    raise error(_message(response))
