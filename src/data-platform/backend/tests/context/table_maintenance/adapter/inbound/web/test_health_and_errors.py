"""Test the application error mapping and that health lives outside the v1 prefix."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotFoundError("gone"), 404),
        (ConflictError("clash"), 409),
        (ValidationError("bad"), 422),
    ],
)
def test_application_errors_map_to_status_and_detail(error: Exception, status: int) -> None:
    """Each application error maps to its HTTP status with the error message as detail."""
    client = build_client(get_table_discovery_settings=StubUseCase(error=error))

    response = client.get("/v1/table-discovery-settings")

    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


def test_healthz_is_not_under_the_v1_prefix() -> None:
    """The health route is not served under the v1 prefix."""
    assert build_client().get("/v1/healthz").status_code == 404
