"""Test that the views repo sends the exact Iceberg REST requests and maps LoadViewResult replies."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.view.polaris import ViewsPolarisRepo
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.catalog.application.port.outbound.view import (
    NamespaceId,
    View,
    ViewId,
    ViewVersion,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

FIXTURE = Path(__file__).parent / "fixtures" / "load_view_result.json"
VIEWS = "/api/catalog/v1/sales/namespaces/retail/views"
TOP = f"{VIEWS}/top_orders"
TOP_ID = ViewId.of("sales", ("retail",), "top_orders")
UUID = "fa6506c3-7681-40c8-86dc-e36561f83385"


def _load_result() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def _error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message, "type": "X", "code": status}})


def _new_view() -> View:
    return View.define(
        id=TOP_ID, query="SELECT 1", dialect="spark", default_namespace=("retail",), timestamp_ms=1762516800000
    )


def test_load_view_maps_current_version_sql():
    """The view's sql, dialect and default namespace are the current version's, not the first or the last."""
    stub = PolarisStub()
    body = _load_result()
    body["metadata"]["current-version-id"] = 1
    stub.on("GET", TOP, httpx.Response(200, json=body))

    view = ViewsPolarisRepo(stub.client()).get(TOP_ID)

    assert view is not None
    assert (view.query, view.dialect, view.default_namespace) == ("SELECT 1", "spark", ("retail",))
    assert view.current_version_id == 1


def test_load_view_maps_uuid_location_schema_versions_and_properties():
    """A real LoadViewResult maps to the view with its current schema, every version and its properties."""
    stub = PolarisStub()
    stub.on("GET", TOP, httpx.Response(200, json=_load_result()))

    view = ViewsPolarisRepo(stub.client()).get(TOP_ID)

    assert view is not None
    assert (view.uuid, view.location) == (UUID, "s3://lakehouse/iceberg/retail/top_orders")
    assert (view.query, view.dialect, view.default_namespace) == (
        "SELECT order_id, amount FROM orders",
        "trino",
        ("retail", "a.b"),
    )
    assert view.schema.schema_id == 1
    assert [(f.id, f.name, f.type, f.required, f.doc) for f in view.schema.fields] == [
        (1, "order_id", "long", True, "key"),
        (2, "amount", "decimal(10,2)", False, None),
        (3, "tags", "list<string>", False, None),
    ]
    assert view.versions == [
        ViewVersion(1, 1762516800000, 0, "SELECT 1", "spark", ("retail",)),
        ViewVersion(2, 1762520400000, 1, "SELECT order_id, amount FROM orders", "trino", ("retail", "a.b")),
    ]
    assert view.properties == {"comment": "top orders"}


def test_load_view_never_reads_the_config_block():
    """The ``config`` block may carry storage credentials; nothing of it reaches the view."""
    stub = PolarisStub()
    stub.on("GET", TOP, httpx.Response(200, json=_load_result()))

    view = ViewsPolarisRepo(stub.client()).get(TOP_ID)

    assert "must-not-leak" not in repr(view)


def test_get_unknown_view_is_none():
    """Polaris's 404 means there is none."""
    stub = PolarisStub()
    stub.on("GET", TOP, _error(404, "View does not exist"))

    assert ViewsPolarisRepo(stub.client()).get(TOP_ID) is None


def _variant(change: Any) -> httpx.Response:  # noqa: ANN401
    body = copy.deepcopy(_load_result())
    change(body["metadata"])
    return httpx.Response(200, json=body)


def _no_sql(metadata: dict[str, Any]) -> None:
    metadata["versions"][1]["representations"] = [{"type": "other", "text": "x"}]


def _old_version_without_sql(metadata: dict[str, Any]) -> None:
    metadata["versions"][0]["representations"] = []


MALFORMED = {
    "not json": httpx.Response(200, text="<html>nope</html>"),
    "no metadata": httpx.Response(200, json={}),
    "list body": httpx.Response(200, json=["metadata"]),
    "current version matches no version": _variant(lambda m: m.update({"current-version-id": 9})),
    "no current version id": _variant(lambda m: m.pop("current-version-id")),
    "current schema matches no schema": _variant(lambda m: m["versions"][1].update({"schema-id": 9})),
    "no schemas": _variant(lambda m: m.pop("schemas")),
    "no uuid": _variant(lambda m: m.pop("view-uuid")),
    "no location": _variant(lambda m: m.pop("location")),
    "no versions": _variant(lambda m: m.pop("versions")),
    "current version has no sql": _variant(_no_sql),
    "older version has no sql": _variant(_old_version_without_sql),
    "default namespace is text": _variant(lambda m: m["versions"][1].update({"default-namespace": "retail"})),
    "sql is not text": _variant(lambda m: m["versions"][1]["representations"][0].update({"sql": None})),
    "properties is a list": _variant(lambda m: m.update({"properties": ["a"]})),
}


@pytest.mark.parametrize("reply", MALFORMED.values(), ids=MALFORMED.keys())
def test_unreadable_view_is_catalog_unavailable(reply: httpx.Response):
    """A reply this backend cannot read answers CatalogUnavailableError naming the view, never a default or a 500."""
    stub = PolarisStub()
    stub.on("GET", TOP, reply)

    with pytest.raises(CatalogUnavailableError, match="view top_orders in a form this backend cannot read"):
        ViewsPolarisRepo(stub.client()).get(TOP_ID)


def test_create_view_sends_view_version():
    """The body carries the name, an empty schema, one view-version with the sql representation and no properties."""
    stub = PolarisStub()
    stub.on("POST", VIEWS, httpx.Response(200, json=_load_result()))

    created = ViewsPolarisRepo(stub.client()).create(_new_view())

    (request,) = stub.requests
    assert json.loads(request.content) == {
        "name": "top_orders",
        "schema": {"type": "struct", "schema-id": 0, "fields": []},
        "view-version": {
            "version-id": 1,
            "timestamp-ms": 1762516800000,
            "schema-id": 0,
            "summary": {"engine-name": "spark", "engine-version": "1.0.0"},
            "representations": [{"type": "sql", "sql": "SELECT 1", "dialect": "spark"}],
            "default-namespace": ["retail"],
        },
        "properties": {},
    }
    assert created.uuid == UUID


def test_create_view_sends_location_only_when_it_has_one():
    """A view defined with a location sends it; one without leaves it to Polaris."""
    stub = PolarisStub()
    stub.on("POST", VIEWS, httpx.Response(200, json=_load_result()))
    view = _new_view()
    view.location = "s3://w/custom"

    ViewsPolarisRepo(stub.client()).create(view)

    (request,) = stub.requests
    assert json.loads(request.content)["location"] == "s3://w/custom"


def test_create_errors_pass_through():
    """A taken name is ConflictError, an unknown namespace NotFoundError, a bad body ValidationError."""
    stub = PolarisStub()
    stub.on("POST", VIEWS, _error(409, "exists"), _error(404, "no namespace"), _error(400, "bad"))
    repo = ViewsPolarisRepo(stub.client())

    with pytest.raises(ConflictError):
        repo.create(_new_view())
    with pytest.raises(NotFoundError):
        repo.create(_new_view())
    with pytest.raises(ValidationError):
        repo.create(_new_view())


def test_create_unreadable_reply_is_catalog_unavailable():
    """A created view Polaris answers unreadably is a 502 message, not a 500."""
    stub = PolarisStub()
    stub.on("POST", VIEWS, httpx.Response(200, json={"metadata": {}}))

    with pytest.raises(CatalogUnavailableError, match="view top_orders in a form this backend cannot read"):
        ViewsPolarisRepo(stub.client()).create(_new_view())


def test_list_in_returns_the_identifiers():
    """The listing maps to ids in the namespace."""
    stub = PolarisStub()
    stub.on("GET", VIEWS, httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": "top_orders"}]}))

    assert ViewsPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",))) == [TOP_ID]


def test_list_in_refuses_a_paged_listing():
    """A next-page-token is CatalogUnavailableError, not a silently cut list (Ruling R8)."""
    stub = PolarisStub()
    stub.on("GET", VIEWS, httpx.Response(200, json={"identifiers": [], "next-page-token": "p2"}))

    with pytest.raises(CatalogUnavailableError, match="paged"):
        ViewsPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_in_unreadable_listing_is_catalog_unavailable():
    """A non-JSON listing is CatalogUnavailableError."""
    stub = PolarisStub()
    stub.on("GET", VIEWS, httpx.Response(200, text="nope"))

    with pytest.raises(CatalogUnavailableError, match="cannot read"):
        ViewsPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_all_walks_every_namespace_and_loads_each_view():
    """list_all visits every catalog's namespaces and loads each view."""
    stub = PolarisStub()
    stub.on("GET", "/api/management/v1/catalogs", httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces",
        httpx.Response(200, json={"namespaces": [["retail"]]}),
        httpx.Response(200, json={"namespaces": []}),
    )
    stub.on("GET", VIEWS, httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": "top_orders"}]}))
    stub.on("GET", TOP, httpx.Response(200, json=_load_result()))

    assert [v.id for v in ViewsPolarisRepo(stub.client()).list_all()] == [TOP_ID]


def test_delete_view_and_unknown_is_not_found():
    """Delete sends a DELETE and answers nothing; a 404 is NotFoundError."""
    stub = PolarisStub()
    stub.on("DELETE", TOP, httpx.Response(204), _error(404, "gone"))
    repo = ViewsPolarisRepo(stub.client())

    repo.delete(TOP_ID)
    with pytest.raises(NotFoundError):
        repo.delete(TOP_ID)
