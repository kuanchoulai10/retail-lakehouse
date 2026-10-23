"""Test the health endpoint and the application error mapping."""

from __future__ import annotations

import pytest
from application.exceptions import ConflictError, NotFoundError, ValidationError
from tests.adapter.inbound.web.web_test_support import StubUseCase, build_client


def test_healthz_returns_200() -> None:
    response = build_client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotFoundError("gone"), 404),
        (ConflictError("clash"), 409),
        (ValidationError("bad"), 422),
    ],
)
def test_application_errors_map_to_status_and_detail(
    error: Exception, status: int
) -> None:
    client = build_client(get_discovery_settings=StubUseCase(error=error))

    response = client.get("/v1/discovery")

    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


def test_healthz_is_not_under_the_v1_prefix() -> None:
    assert build_client().get("/v1/healthz").status_code == 404
