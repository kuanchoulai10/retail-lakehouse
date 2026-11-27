"""Test the application error mapping and that health lives outside the v1 prefix."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.exceptions import (
    ConcurrentUpdateError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError, CatalogNotFoundError
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotFoundError("gone"), 404),
        (ConflictError("clash"), 409),
        (ConcurrentUpdateError("table u1 was changed by someone else"), 409),
        (ValidationError("bad"), 422),
    ],
)
def test_application_errors_map_to_status_and_detail(error: Exception, status: int) -> None:
    """Each application error maps to its HTTP status with the error message as detail."""
    client = build_client(list_table_discovery_policies=StubUseCase(error=error))

    response = client.get("/v1/discovery-policies")

    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


def test_healthz_is_not_under_the_v1_prefix() -> None:
    """The health route is not served under the v1 prefix."""
    assert build_client().get("/v1/healthz").status_code == 404


def test_refused_catalog_maps_to_403() -> None:
    """A catalog the platform's credential cannot read answers 403 with the message as detail."""
    error = CatalogAccessDeniedError("secret")
    client = build_client(list_table_commits=StubUseCase(error=error))

    response = client.get("/v1/tables/u-1/commits")

    assert response.status_code == 403
    assert response.json() == {"detail": "the platform's catalog credential cannot read catalog secret"}


def test_unknown_catalog_maps_to_404() -> None:
    """A catalog the gateway does not know answers 404 with the message as detail."""
    error = CatalogNotFoundError("nope")
    client = build_client(list_table_commits=StubUseCase(error=error))

    response = client.get("/v1/tables/u-1/commits")

    assert response.status_code == 404
    assert response.json() == {"detail": "catalog nope not found"}
