"""Test that register_routes stores the use cases and maps the catalog exceptions to HTTP errors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import build_app


def test_use_cases_are_stored_under_the_catalog_key():
    """The use cases live under their own app state key, beside any other context's."""
    app = build_app()

    assert app.state.catalog_use_cases is not None


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotFoundError("catalog nope not found"), 404),
        (ConflictError("changed since you loaded it, reload"), 409),
        (ValidationError("name must not be blank"), 422),
        (PermissionDeniedError("not authorized for op CREATE_NAMESPACE"), 403),
        (CatalogUnavailableError("Polaris is unreachable: connection refused"), 502),
    ],
)
def test_catalog_exceptions_map_to_status_with_detail(error: Exception, status: int):
    """Each catalog exception becomes its status, with the message as the detail."""
    app = build_app()

    @app.get("/boom")
    def boom() -> None:
        raise error

    response = TestClient(app).get("/boom")

    assert response.status_code == status
    assert response.json() == {"detail": str(error)}
