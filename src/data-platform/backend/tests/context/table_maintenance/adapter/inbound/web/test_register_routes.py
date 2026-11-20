"""Test that register_routes mounts the table maintenance routes on a bare app."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from context.table_maintenance.application.port.inbound.table import (
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    StubUseCase,
    build_client,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


def test_register_routes_mounts_table_routes_under_v1() -> None:
    """GET /v1/tables reaches the list-tables use case."""
    stub = StubUseCase(ListTablesUseCaseOutput(items=()))

    response = build_client(list_tables=stub).get("/v1/tables")

    assert response.status_code == 200
    assert stub.requests == [ListTablesUseCaseInput(status=None)]


def _paths() -> set[str]:
    return {getattr(route, "path", "") for route in cast("FastAPI", build_client().app).routes}


def test_register_routes_mounts_the_platform_settings_route() -> None:
    """The platform settings stay readable."""
    assert "/v1/platform-settings" in _paths()


def test_register_routes_mounts_no_route_for_rounds_or_candidates() -> None:
    """Compaction rounds, their scheduler settings and the compaction candidates have no route any more."""
    paths = _paths()
    assert "/v1/compaction-rounds" not in paths
    assert "/v1/compaction-rounds/{round_id}" not in paths
    assert "/v1/scheduler-settings" not in paths
    assert "/v1/tables/{table_uuid}/compaction-candidates" not in paths
