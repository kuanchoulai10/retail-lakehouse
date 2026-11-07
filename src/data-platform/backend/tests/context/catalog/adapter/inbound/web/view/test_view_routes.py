"""Test the view routes."""

from __future__ import annotations

from typing import Any

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.inbound.generic_table import (
    DeleteGenericTableUseCaseInput,
    DeleteGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.view import (
    CreateViewUseCaseInput,
    CreateViewUseCaseOutput,
    DeleteViewUseCaseInput,
    DeleteViewUseCaseOutput,
    GetViewUseCaseInput,
    GetViewUseCaseOutput,
    ListViewsUseCaseInput,
    ListViewsUseCaseOutput,
    ListViewsUseCaseOutputItem,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client

BASE = "/v1/catalogs/sales/namespaces/retail/views"


def _fields() -> dict[str, Any]:
    return {
        "catalog": "sales",
        "namespace": ["retail"],
        "name": "top_orders",
        "uuid": "view-uuid-1",
        "location": "s3://w/retail/top_orders",
        "query": "SELECT 2",
        "dialect": "trino",
        "default_namespace": ["retail"],
        "current_version_id": 2,
        "schema": {
            "schema_id": 1,
            "fields": [{"id": 1, "name": "order_id", "type": "long", "required": True, "doc": None}],
        },
        "versions": [
            {"version_id": 1, "timestamp_ms": 10, "query": "SELECT 1"},
            {"version_id": 2, "timestamp_ms": 20, "query": "SELECT 2"},
        ],
        "properties": {"comment": "top"},
    }


def test_get_view_returns_sql_schema_versions_and_properties():
    """Get returns everything the view page shows, the sql as ``sql``; version ids stay numbers."""
    stub = StubUseCase(GetViewUseCaseOutput(**_fields()))

    response = build_client(get_view=stub).get(f"{BASE}/top_orders")

    expected = _fields()
    expected["sql"] = expected.pop("query")
    for version in expected["versions"]:
        version["sql"] = version.pop("query")
    assert (response.status_code, response.json()) == (200, expected)
    assert stub.requests == [GetViewUseCaseInput("sales", ["retail"], "top_orders")]


def test_get_unknown_view_returns_404():
    """A missing view is a 404 with the message."""
    client = build_client(get_view=StubUseCase(error=NotFoundError("view top_orders not found")))

    response = client.get(f"{BASE}/top_orders")

    assert (response.status_code, response.json()) == (404, {"detail": "view top_orders not found"})


def test_view_route_splits_the_namespace_on_the_unit_separator():
    """``a%1Fb.c`` in the path is the parts a and b.c."""
    stub = StubUseCase(GetViewUseCaseOutput(**_fields()))

    build_client(get_view=stub).get("/v1/catalogs/sales/namespaces/a%1Fb.c/views/top_orders")

    assert stub.requests == [GetViewUseCaseInput("sales", ["a", "b.c"], "top_orders")]


def test_list_views():
    """Listing returns the identifiers."""
    stub = StubUseCase(ListViewsUseCaseOutput([ListViewsUseCaseOutputItem("sales", ["retail"], "top_orders")]))

    response = build_client(list_views=stub).get(BASE)

    assert response.json() == [{"catalog": "sales", "namespace": ["retail"], "name": "top_orders"}]
    assert stub.requests == [ListViewsUseCaseInput("sales", ["retail"])]


def test_create_view_returns_201_and_passes_the_form():
    """Create passes name, sql and dialect."""
    stub = StubUseCase(CreateViewUseCaseOutput(**_fields()))

    response = build_client(create_view=stub).post(
        BASE, json={"name": "top_orders", "sql": "SELECT 2", "dialect": "trino"}
    )

    assert (response.status_code, response.json()["uuid"]) == (201, "view-uuid-1")
    assert stub.requests == [CreateViewUseCaseInput("sales", ["retail"], "top_orders", "SELECT 2", "trino")]


def test_create_view_needs_sql_and_dialect_and_rejects_unknown_fields():
    """A body without sql or dialect, or with a field the form does not have, is refused."""
    stub = StubUseCase()
    client = build_client(create_view=stub)

    assert client.post(BASE, json={"name": "v", "dialect": "spark"}).status_code == 422
    assert client.post(BASE, json={"name": "v", "sql": "SELECT 1"}).status_code == 422
    assert client.post(BASE, json={"name": "v", "sql": "SELECT 1", "dialect": "spark", "schema": {}}).status_code == 422
    assert stub.requests == []


def test_create_view_conflict_is_409():
    """A taken name is a 409."""
    client = build_client(create_view=StubUseCase(error=ConflictError("exists")))

    response = client.post(BASE, json={"name": "v", "sql": "SELECT 1", "dialect": "spark"})

    assert (response.status_code, response.json()) == (409, {"detail": "exists"})


def test_delete_view_and_generic_table_return_204():
    """Both deletes answer 204 with no body and pass the identity on."""
    view_stub = StubUseCase(DeleteViewUseCaseOutput())
    table_stub = StubUseCase(DeleteGenericTableUseCaseOutput())
    client = build_client(delete_view=view_stub, delete_generic_table=table_stub)

    view = client.delete(f"{BASE}/top_orders")
    table = client.delete("/v1/catalogs/sales/namespaces/retail/generic-tables/events")

    assert [(r.status_code, r.content) for r in (view, table)] == [(204, b""), (204, b"")]
    assert view_stub.requests == [DeleteViewUseCaseInput("sales", ["retail"], "top_orders")]
    assert table_stub.requests == [DeleteGenericTableUseCaseInput("sales", ["retail"], "events")]
