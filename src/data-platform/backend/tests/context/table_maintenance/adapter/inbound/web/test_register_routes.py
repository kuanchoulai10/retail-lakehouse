"""Test that register_routes mounts the table maintenance routes on a bare app."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table import (
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)


def test_register_routes_mounts_table_routes_under_v1() -> None:
    """GET /v1/tables reaches the list-tables use case."""
    stub = StubUseCase(ListTablesUseCaseOutput(items=[]))

    response = build_client(list_tables=stub).get("/v1/tables")

    assert response.status_code == 200
    assert stub.requests == [ListTablesUseCaseInput(status=None)]
