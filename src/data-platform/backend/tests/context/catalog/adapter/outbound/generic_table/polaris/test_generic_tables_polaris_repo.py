"""Test that the generic tables repo sends the exact Polaris API requests and maps its replies."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.generic_table.polaris import GenericTablesPolarisRepo
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.catalog.application.port.outbound.generic_table import (
    GenericTable,
    GenericTableId,
    NamespaceId,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

TABLES = "/api/catalog/polaris/v1/sales/namespaces/retail/generic-tables"
EVENTS = f"{TABLES}/events"
EVENTS_ID = GenericTableId.of("sales", ("retail",), "events")
REPLY = {
    "table": {
        "name": "events",
        "format": "delta",
        "base-location": "s3://w/events",
        "doc": "clicks",
        "properties": {"owner": "data-eng"},
    }
}


def _error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message, "type": "X", "code": status}})


def _events() -> GenericTable:
    return GenericTable(
        id=EVENTS_ID, format="delta", base_location="s3://w/events", doc="clicks", properties={"owner": "data-eng"}
    )


def test_generic_table_paths_use_polaris_api_prefix():
    """Generic tables live under /api/catalog/polaris/v1, not under the Iceberg REST /api/catalog/v1."""
    stub = PolarisStub()
    stub.on("GET", EVENTS, httpx.Response(200, json=REPLY))
    stub.on("GET", TABLES, httpx.Response(200, json={"identifiers": []}))
    stub.on("DELETE", EVENTS, httpx.Response(204))
    repo = GenericTablesPolarisRepo(stub.client())

    repo.get(EVENTS_ID)
    repo.list_in(NamespaceId.of("sales", ("retail",)))
    repo.delete(EVENTS_ID)

    assert [(r.method, r.url.raw_path.decode()) for r in stub.requests] == [
        ("GET", EVENTS),
        ("GET", TABLES),
        ("DELETE", EVENTS),
    ]


def test_namespace_part_with_a_dot_and_a_nested_namespace_are_encoded_into_the_path():
    """A nested namespace is joined by %1F; a part with a dot stays one part."""
    stub = PolarisStub()
    path = "/api/catalog/polaris/v1/sales/namespaces/a.b%1Fc/generic-tables/events"
    stub.on("GET", path, httpx.Response(200, json=REPLY))

    table = GenericTablesPolarisRepo(stub.client()).get(GenericTableId.of("sales", ("a.b", "c"), "events"))

    assert table is not None


def test_get_maps_format_base_location_doc_and_properties():
    """The reply's ``table`` maps to a GenericTable."""
    stub = PolarisStub()
    stub.on("GET", EVENTS, httpx.Response(200, json=REPLY))

    table = GenericTablesPolarisRepo(stub.client()).get(EVENTS_ID)

    assert table == _events()


def test_get_without_optional_fields_leaves_them_empty():
    """A reply with no base location, doc or properties maps to None and an empty dict."""
    stub = PolarisStub()
    stub.on("GET", EVENTS, httpx.Response(200, json={"table": {"name": "events", "format": "lance"}}))

    table = GenericTablesPolarisRepo(stub.client()).get(EVENTS_ID)

    assert table is not None
    assert (table.format, table.base_location, table.doc, table.properties) == ("lance", None, None, {})


def test_get_unknown_generic_table_is_none():
    """Polaris's 404 means there is none."""
    stub = PolarisStub()
    stub.on("GET", EVENTS, _error(404, "Generic table does not exist: retail.events"))

    assert GenericTablesPolarisRepo(stub.client()).get(EVENTS_ID) is None


@pytest.mark.parametrize(
    "reply",
    [
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"table": "events"}),
        httpx.Response(200, json={"table": {"name": "events"}}),
        httpx.Response(200, json={"table": {"name": "events", "format": "delta", "properties": ["a"]}}),
        httpx.Response(200, json=["table"]),
    ],
)
def test_unreadable_generic_table_is_catalog_unavailable(reply: httpx.Response):
    """A reply this backend cannot read answers CatalogUnavailableError naming the table, never a bare exception."""
    stub = PolarisStub()
    stub.on("GET", EVENTS, reply)

    with pytest.raises(CatalogUnavailableError, match="generic table events in a form this backend cannot read"):
        GenericTablesPolarisRepo(stub.client()).get(EVENTS_ID)


def test_create_sends_name_format_location_doc_and_properties():
    """The body is the Polaris CreateGenericTableRequest; the reply is mapped."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json=REPLY))

    created = GenericTablesPolarisRepo(stub.client()).create(_events())

    (request,) = stub.requests
    body: Any = json.loads(request.content)
    assert body == {
        "name": "events",
        "format": "delta",
        "base-location": "s3://w/events",
        "doc": "clicks",
        "properties": {"owner": "data-eng"},
    }
    assert created == _events()


def test_create_leaves_out_an_absent_location_and_doc():
    """A missing base location or doc is not sent."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json={"table": {"name": "events", "format": "delta"}}))

    GenericTablesPolarisRepo(stub.client()).create(GenericTable(EVENTS_ID, "delta", None, None, {}))

    (request,) = stub.requests
    assert json.loads(request.content) == {"name": "events", "format": "delta", "properties": {}}


def test_create_errors_pass_through():
    """A taken name is ConflictError and an unknown namespace NotFoundError; neither is swallowed as unreadable."""
    stub = PolarisStub()
    stub.on("POST", TABLES, _error(409, "exists"), _error(404, "no namespace"), _error(400, "bad"))
    repo = GenericTablesPolarisRepo(stub.client())

    with pytest.raises(ConflictError):
        repo.create(_events())
    with pytest.raises(NotFoundError):
        repo.create(_events())
    with pytest.raises(ValidationError):
        repo.create(_events())


def test_list_in_returns_the_identifiers():
    """The listing maps to ids in the namespace."""
    stub = PolarisStub()
    stub.on(
        "GET",
        TABLES,
        httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": "events"}]}),
    )

    found = GenericTablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))

    assert found == [EVENTS_ID]


def test_list_in_refuses_a_paged_listing():
    """A next-page-token is CatalogUnavailableError, not a silently cut list (Ruling R8)."""
    stub = PolarisStub()
    stub.on("GET", TABLES, httpx.Response(200, json={"identifiers": [], "next-page-token": "p2"}))

    with pytest.raises(CatalogUnavailableError, match="paged"):
        GenericTablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_in_unreadable_listing_is_catalog_unavailable():
    """An identifier without a namespace list is CatalogUnavailableError."""
    stub = PolarisStub()
    stub.on("GET", TABLES, httpx.Response(200, json={"identifiers": [{"name": "events"}]}))

    with pytest.raises(CatalogUnavailableError, match="cannot read"):
        GenericTablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_in_unknown_namespace_is_not_found():
    """A 404 on the listing is NotFoundError."""
    stub = PolarisStub()
    stub.on("GET", TABLES, _error(404, "Namespace does not exist"))

    with pytest.raises(NotFoundError):
        GenericTablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_all_walks_every_namespace_and_loads_each_generic_table():
    """list_all visits every catalog's namespaces and loads each generic table."""
    stub = PolarisStub()
    stub.on("GET", "/api/management/v1/catalogs", httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces",
        httpx.Response(200, json={"namespaces": [["retail"]]}),
        httpx.Response(200, json={"namespaces": []}),
    )
    stub.on("GET", TABLES, httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": "events"}]}))
    stub.on("GET", EVENTS, httpx.Response(200, json=REPLY))

    assert GenericTablesPolarisRepo(stub.client()).list_all() == [_events()]


def test_delete_sends_a_delete_and_unknown_is_not_found():
    """Delete answers nothing on success and NotFoundError on a 404."""
    stub = PolarisStub()
    stub.on("DELETE", EVENTS, httpx.Response(204), _error(404, "gone"))
    repo = GenericTablesPolarisRepo(stub.client())

    repo.delete(EVENTS_ID)
    with pytest.raises(NotFoundError):
        repo.delete(EVENTS_ID)


@pytest.mark.parametrize(("name", "encoded"), [("my table", "my%20table"), ("a/b?c", "a%2Fb%3Fc")])
def test_generic_table_name_is_percent_encoded_as_one_path_segment_in_the_raw_path(name: str, encoded: str):
    """A space becomes %20 and ``/`` or ``?`` stay inside the one segment, never split or left raw."""
    stub = PolarisStub()
    stub.on("GET", f"{TABLES}/{encoded}", httpx.Response(200, json=REPLY))
    stub.on("DELETE", f"{TABLES}/{encoded}", httpx.Response(204))
    repo = GenericTablesPolarisRepo(stub.client())
    item_id = GenericTableId.of("sales", ("retail",), name)

    assert repo.get(item_id) is not None
    repo.delete(item_id)

    assert [(r.method, r.url.raw_path.decode()) for r in stub.requests] == [
        ("GET", f"{TABLES}/{encoded}"),
        ("DELETE", f"{TABLES}/{encoded}"),
    ]
