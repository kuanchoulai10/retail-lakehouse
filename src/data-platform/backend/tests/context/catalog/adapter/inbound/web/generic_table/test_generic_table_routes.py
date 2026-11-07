"""Test the generic table routes."""

from __future__ import annotations

from typing import Any

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.inbound.generic_table import (
    CreateGenericTableUseCaseInput,
    CreateGenericTableUseCaseOutput,
    DeleteGenericTableUseCaseInput,
    DeleteGenericTableUseCaseOutput,
    GetGenericTableUseCaseInput,
    GetGenericTableUseCaseOutput,
    ListGenericTablesUseCaseInput,
    ListGenericTablesUseCaseOutput,
    ListGenericTablesUseCaseOutputItem,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client

BASE = "/v1/catalogs/sales/namespaces/retail/generic-tables"


def _fields() -> dict[str, Any]:
    return {
        "catalog": "sales",
        "namespace": ["retail"],
        "name": "events",
        "format": "delta",
        "base_location": "s3://w/events",
        "doc": "clicks",
        "properties": {"owner": "data-eng"},
    }


def test_get_generic_table_returns_its_fields():
    """Get returns format, base location, doc and properties."""
    stub = StubUseCase(GetGenericTableUseCaseOutput(**_fields()))

    response = build_client(get_generic_table=stub).get(f"{BASE}/events")

    assert (response.status_code, response.json()) == (200, _fields())
    assert stub.requests == [GetGenericTableUseCaseInput("sales", ["retail"], "events")]


def test_get_generic_table_without_location_and_doc_has_nulls():
    """An absent base location and doc are null."""
    fields = _fields()
    fields["base_location"] = None
    fields["doc"] = None

    response = build_client(get_generic_table=StubUseCase(GetGenericTableUseCaseOutput(**fields))).get(f"{BASE}/events")

    assert (response.json()["base_location"], response.json()["doc"]) == (None, None)


def test_get_unknown_generic_table_returns_404():
    """A missing generic table is a 404 with the message."""
    client = build_client(get_generic_table=StubUseCase(error=NotFoundError("generic table events not found")))

    response = client.get(f"{BASE}/events")

    assert (response.status_code, response.json()) == (404, {"detail": "generic table events not found"})


def test_generic_table_route_splits_the_namespace_on_the_unit_separator():
    """``a%1Fb.c`` in the path is the parts a and b.c."""
    stub = StubUseCase(GetGenericTableUseCaseOutput(**_fields()))

    build_client(get_generic_table=stub).get("/v1/catalogs/sales/namespaces/a%1Fb.c/generic-tables/events")

    assert stub.requests == [GetGenericTableUseCaseInput("sales", ["a", "b.c"], "events")]


def test_list_generic_tables():
    """Listing returns the identifiers."""
    stub = StubUseCase(
        ListGenericTablesUseCaseOutput([ListGenericTablesUseCaseOutputItem("sales", ["retail"], "events")])
    )

    response = build_client(list_generic_tables=stub).get(BASE)

    assert response.json() == [{"catalog": "sales", "namespace": ["retail"], "name": "events"}]
    assert stub.requests == [ListGenericTablesUseCaseInput("sales", ["retail"])]


def test_create_generic_table_returns_201_and_passes_the_form():
    """Create passes name, format, base location, doc and properties."""
    stub = StubUseCase(CreateGenericTableUseCaseOutput(**_fields()))

    response = build_client(create_generic_table=stub).post(
        BASE,
        json={
            "name": "events",
            "format": "delta",
            "base_location": "s3://w/events",
            "doc": "clicks",
            "properties": {"owner": "data-eng"},
        },
    )

    assert (response.status_code, response.json()) == (201, _fields())
    assert stub.requests == [
        CreateGenericTableUseCaseInput(
            "sales", ["retail"], "events", "delta", "s3://w/events", "clicks", {"owner": "data-eng"}
        )
    ]


def test_create_generic_table_needs_a_format_and_rejects_unknown_fields():
    """A body without a format, or with a field the form does not have, is refused."""
    stub = StubUseCase()
    client = build_client(create_generic_table=stub)

    assert client.post(BASE, json={"name": "events"}).status_code == 422
    assert client.post(BASE, json={"name": "events", "format": "delta", "schema": []}).status_code == 422
    assert stub.requests == []


def test_create_generic_table_conflict_is_409():
    """A taken name is a 409."""
    client = build_client(create_generic_table=StubUseCase(error=ConflictError("exists")))

    response = client.post(BASE, json={"name": "events", "format": "delta"})

    assert (response.status_code, response.json()) == (409, {"detail": "exists"})


def test_delete_generic_table_returns_204():
    """Delete returns 204 with no body."""
    stub = StubUseCase(DeleteGenericTableUseCaseOutput())

    response = build_client(delete_generic_table=stub).delete(f"{BASE}/events")

    assert (response.status_code, response.content) == (204, b"")
    assert stub.requests == [DeleteGenericTableUseCaseInput("sales", ["retail"], "events")]
