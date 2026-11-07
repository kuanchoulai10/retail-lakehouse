"""Test that Polaris error responses become the catalog application exceptions."""

from __future__ import annotations

import httpx
import pytest

from context.catalog.adapter.outbound.shared.polaris import raise_for_polaris
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


def _polaris_error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message, "type": "SomeException", "code": status}})


def test_polaris_forbidden_maps_to_permission_denied():
    """A 403 carries Polaris's own message from ``error.message``."""
    message = "Principal 'root' with activated PrincipalRoles '[]' is not authorized for op CREATE_NAMESPACE"

    with pytest.raises(PermissionDeniedError) as raised:
        raise_for_polaris(_polaris_error(403, message))

    assert str(raised.value) == message


def test_conflict_maps_to_conflict():
    """A 409 is a conflict with Polaris's message."""
    with pytest.raises(ConflictError, match="^Catalog already exists: iceberg$"):
        raise_for_polaris(_polaris_error(409, "Catalog already exists: iceberg"))


def test_not_found_maps_to_not_found():
    """A 404 is a not-found with Polaris's message."""
    with pytest.raises(NotFoundError, match="^Catalog not found: nope$"):
        raise_for_polaris(_polaris_error(404, "Catalog not found: nope"))


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (400, ValidationError),
        (422, ValidationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (405, CatalogUnavailableError),
        (500, CatalogUnavailableError),
        (503, CatalogUnavailableError),
    ],
)
def test_status_mapping(status: int, error: type[Exception]):
    """Each error status maps to its application exception; any other error status is unavailable."""
    with pytest.raises(error, match="^boom$"):
        raise_for_polaris(_polaris_error(status, "boom"))


def test_unauthorized_is_the_backend_credential_being_rejected():
    """Every request carries the backend's own credential, so a 401 is an upstream fault, not a user privilege."""
    with pytest.raises(CatalogUnavailableError, match="^the catalog rejected the backend credential: expired$"):
        raise_for_polaris(_polaris_error(401, "expired"))


@pytest.mark.parametrize("status", [200, 201, 204, 304])
def test_success_passes(status: int):
    """A response below 400 raises nothing."""
    raise_for_polaris(httpx.Response(status))


def test_body_without_error_message_falls_back_to_raw_text():
    """A body that is not a Polaris error object is reported as its raw text."""
    with pytest.raises(CatalogUnavailableError, match="^upstream connect error$"):
        raise_for_polaris(httpx.Response(503, text="upstream connect error"))


def test_json_body_without_error_message_falls_back_to_raw_text():
    """A JSON body without ``error.message`` is reported as its raw text."""
    with pytest.raises(ValidationError, match='^{"detail":"bad"}$'):
        raise_for_polaris(httpx.Response(400, content=b'{"detail":"bad"}'))


def test_empty_body_falls_back_to_the_status():
    """An empty body still yields a message that names the status."""
    with pytest.raises(NotFoundError, match="^HTTP 404 Not Found$"):
        raise_for_polaris(httpx.Response(404))
