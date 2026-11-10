"""Test that the namespaces repo sends the exact Iceberg REST requests and maps the replies."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.namespace.polaris import NamespacesPolarisRepo
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.catalog.application.port.outbound.namespace import CatalogId, Namespace, NamespaceId
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

NAMESPACES = "/api/catalog/v1/sales/namespaces"
CATALOGS = "/api/management/v1/catalogs"


def _body(request: httpx.Request) -> Any:  # noqa: ANN401
    return json.loads(request.content)


def _error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message, "type": "X", "code": status}})


def test_create_posts_the_namespace_with_properties():
    """Create sends POST /namespaces with the parts and properties and returns what Polaris saved."""
    stub = PolarisStub()
    stub.on("POST", NAMESPACES, httpx.Response(200, json={"namespace": ["raw"], "properties": {"owner": "de"}}))

    saved = NamespacesPolarisRepo(stub.client()).create(
        Namespace(id=NamespaceId.of("sales", ("raw",)), properties={"owner": "de"})
    )

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("POST", NAMESPACES)
    assert _body(request) == {"namespace": ["raw"], "properties": {"owner": "de"}}
    assert (saved.id, saved.properties) == (NamespaceId.of("sales", ("raw",)), {"owner": "de"})


def test_namespace_part_with_dot_round_trips():
    """``a.b`` goes to Polaris as one part and comes back as one part, in a body and in a path."""
    stub = PolarisStub()
    stub.on("POST", NAMESPACES, httpx.Response(200, json={"namespace": ["a.b"], "properties": {}}))
    stub.on("GET", f"{NAMESPACES}/a.b", httpx.Response(200, json={"namespace": ["a.b"], "properties": {"k": "v"}}))
    repo = NamespacesPolarisRepo(stub.client())

    created = repo.create(Namespace(id=NamespaceId.of("sales", ("a.b",)), properties={}))
    fetched = repo.get(NamespaceId.of("sales", ("a.b",)))

    assert _body(stub.requests[0])["namespace"] == ["a.b"]
    assert created.id.parts == ("a.b",)
    assert fetched is not None
    assert fetched.id.parts == ("a.b",)
    assert fetched.properties == {"k": "v"}


def test_multi_part_namespace_path_joins_parts_with_an_encoded_unit_separator():
    """A nested namespace is ``a%1Fb`` in the path, never ``a.b``, and spaces are encoded."""
    stub = PolarisStub()
    stub.on("GET", f"{NAMESPACES}/a%1Fb%20c", httpx.Response(200, json={"namespace": ["a", "b c"], "properties": {}}))

    fetched = NamespacesPolarisRepo(stub.client()).get(NamespaceId.of("sales", ("a", "b c")))

    assert fetched is not None
    assert fetched.id.parts == ("a", "b c")


def test_get_unknown_namespace_is_none():
    """Polaris's 404 means there is no such namespace."""
    stub = PolarisStub()
    stub.on("GET", f"{NAMESPACES}/nope", _error(404, "Namespace does not exist: nope"))

    assert NamespacesPolarisRepo(stub.client()).get(NamespaceId.of("sales", ("nope",))) is None


def test_list_in_top_level_sends_no_parent_and_returns_each_namespace():
    """Listing the top level sends no ``parent`` and maps each returned namespace."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, httpx.Response(200, json={"namespaces": [["raw"], ["a.b"]]}))

    found = NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ())

    (request,) = stub.requests
    assert "parent" not in request.url.params
    assert [n.id for n in found] == [NamespaceId.of("sales", ("raw",)), NamespaceId.of("sales", ("a.b",))]


def test_list_namespaces_returns_direct_children():
    """Listing with a parent sends ``parent`` joined by U+001F and returns the children Polaris names."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, httpx.Response(200, json={"namespaces": [["a", "b"], ["a", "c.d"]]}))

    found = NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ("a", "x.y"))

    (request,) = stub.requests
    assert request.url.params["parent"] == "a\x1fx.y"
    assert "parent=a%1Fx.y" in request.url.query.decode()
    assert [n.id.parts for n in found] == [("a", "b"), ("a", "c.d")]


def test_list_in_unknown_catalog_is_not_found():
    """Polaris's 404 for an unknown catalog or parent passes through."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, _error(404, "Catalog sales not found"))

    with pytest.raises(NotFoundError, match="Catalog sales not found"):
        NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ())


def test_create_existing_namespace_is_a_conflict():
    """Polaris's 409 is a ConflictError carrying its message."""
    stub = PolarisStub()
    stub.on("POST", NAMESPACES, _error(409, "Namespace already exists: raw"))

    with pytest.raises(ConflictError, match="already exists"):
        NamespacesPolarisRepo(stub.client()).create(Namespace(id=NamespaceId.of("sales", ("raw",)), properties={}))


def test_delete_sends_delete_on_the_namespace_path():
    """Delete sends DELETE on the encoded namespace path."""
    stub = PolarisStub()
    stub.on("DELETE", f"{NAMESPACES}/a%1Fb", httpx.Response(204))

    NamespacesPolarisRepo(stub.client()).delete(NamespaceId.of("sales", ("a", "b")))

    (request,) = stub.requests
    assert (request.method, request.url.raw_path.decode()) == ("DELETE", f"{NAMESPACES}/a%1Fb")


@pytest.mark.parametrize(("status", "error"), [(409, ConflictError), (400, ValidationError)])
def test_delete_non_empty_namespace_reports_polaris_error(status: int, error: type[Exception]):
    """A 409 or 400 for a namespace that is not empty reaches the caller with Polaris's message."""
    stub = PolarisStub()
    stub.on("DELETE", f"{NAMESPACES}/raw", _error(status, "Namespace raw is not empty"))

    with pytest.raises(error, match="Namespace raw is not empty"):
        NamespacesPolarisRepo(stub.client()).delete(NamespaceId.of("sales", ("raw",)))


def _properties_stub() -> PolarisStub:
    stub = PolarisStub()
    stub.on(
        "POST", f"{NAMESPACES}/raw/properties", httpx.Response(200, json={"updated": [], "removed": [], "missing": []})
    )
    stub.on(
        "GET", f"{NAMESPACES}/raw", httpx.Response(200, json={"namespace": ["raw"], "properties": {"tier": "gold"}})
    )
    return stub


def test_update_namespace_properties_sends_removals_then_updates_as_two_requests():
    """Removals and updates go in two POSTs to ``/properties``, then the namespace is read back.

    Polaris 1.8.0 answers one request that holds both with 409 "Concurrent modification of
    namespace" (found live in the e2e), so each request carries one kind of change.
    """
    stub = _properties_stub()

    saved = NamespacesPolarisRepo(stub.client()).update_properties(
        NamespaceId.of("sales", ("raw",)), {"tier": "gold"}, ["stale"]
    )

    remove, update, read = stub.requests
    assert (remove.method, remove.url.path) == ("POST", f"{NAMESPACES}/raw/properties")
    assert _body(remove) == {"removals": ["stale"]}
    assert (update.method, update.url.path) == ("POST", f"{NAMESPACES}/raw/properties")
    assert _body(update) == {"updates": {"tier": "gold"}}
    assert read.method == "GET"
    assert saved.properties == {"tier": "gold"}


@pytest.mark.parametrize(
    ("updates", "removals", "body"),
    [({"tier": "gold"}, [], {"updates": {"tier": "gold"}}), ({}, ["stale"], {"removals": ["stale"]})],
)
def test_update_namespace_properties_sends_one_request_for_one_kind_of_change(
    updates: dict[str, str], removals: list[str], body: dict[str, Any]
):
    """Only updates, or only removals, is one POST holding just that change."""
    stub = _properties_stub()

    NamespacesPolarisRepo(stub.client()).update_properties(NamespaceId.of("sales", ("raw",)), updates, removals)

    post, read = stub.requests
    assert _body(post) == body
    assert read.method == "GET"


def test_list_all_walks_every_catalog_and_every_level():
    """list_all lists the catalogs, then each catalog's namespaces level by level, reading properties."""
    stub = PolarisStub()
    stub.on("GET", CATALOGS, httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on(
        "GET",
        NAMESPACES,
        httpx.Response(200, json={"namespaces": [["a"]]}),
        httpx.Response(200, json={"namespaces": [["a", "b"]]}),
        httpx.Response(200, json={"namespaces": []}),
    )
    stub.on("GET", f"{NAMESPACES}/a", httpx.Response(200, json={"namespace": ["a"], "properties": {}}))
    stub.on("GET", f"{NAMESPACES}/a%1Fb", httpx.Response(200, json={"namespace": ["a", "b"], "properties": {}}))

    found = NamespacesPolarisRepo(stub.client()).list_all()

    assert [n.id.parts for n in found] == [("a",), ("a", "b")]


def test_list_in_refuses_a_paged_listing_instead_of_truncating():
    """A non-null next-page-token means Polaris holds more than it returned; that is a loud 502, not a short list."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, httpx.Response(200, json={"namespaces": [["a"]], "next-page-token": "tok"}))

    with pytest.raises(CatalogUnavailableError, match="paged listing"):
        NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ())


def test_list_in_accepts_a_null_next_page_token():
    """A null token is the last page, so the listing is complete."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, httpx.Response(200, json={"namespaces": [["a"]], "next-page-token": None}))

    found = NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ())

    assert [n.id.parts for n in found] == [("a",)]


_HTML = httpx.Response(200, text="<html>proxy error</html>", headers={"content-type": "text/html"})
_JSON_LIST = httpx.Response(200, json=[["raw"]])
_RAW = NamespaceId.of("sales", ("raw",))
_OPERATIONS = {
    "create": ("POST", NAMESPACES, lambda repo: repo.create(Namespace(id=_RAW, properties={}))),
    "get": ("GET", f"{NAMESPACES}/raw", lambda repo: repo.get(_RAW)),
    "list_in": ("GET", NAMESPACES, lambda repo: repo.list_in(CatalogId.of("sales"), ())),
    "list_all": ("GET", CATALOGS, lambda repo: repo.list_all()),
    "update_properties": ("GET", f"{NAMESPACES}/raw", lambda repo: repo.update_properties(_RAW, {}, [])),
}


@pytest.mark.parametrize("operation", sorted(_OPERATIONS))
@pytest.mark.parametrize("reply", [_HTML, _JSON_LIST], ids=["html", "json-list"])
def test_unreadable_reply_is_unavailable_on_every_operation(operation: str, reply: httpx.Response):
    """A 200 that is HTML or not a JSON object is a CatalogUnavailableError (502), never a 500."""
    method, path, call = _OPERATIONS[operation]
    stub = PolarisStub()
    stub.on(method, path, reply)

    with pytest.raises(CatalogUnavailableError, match="in a form this backend cannot read"):
        call(NamespacesPolarisRepo(stub.client()))


@pytest.mark.parametrize(
    "body",
    [{"properties": {}}, {"namespace": "raw", "properties": {}}, {"namespace": ["raw"], "properties": ["k"]}],
    ids=["no-namespace", "string-namespace", "list-properties"],
)
def test_namespace_reply_of_the_wrong_shape_is_unavailable(body: dict[str, Any]):
    """A missing namespace is never ``()`` and a string is never split into characters; both are a 502."""
    stub = PolarisStub()
    stub.on("GET", f"{NAMESPACES}/raw", httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="namespace \\['raw'\\] in a form this backend cannot read"):
        NamespacesPolarisRepo(stub.client()).get(_RAW)


@pytest.mark.parametrize(
    "body",
    [{}, {"namespaces": ["raw"]}, {"namespaces": [["raw", 1]]}, {"namespaces": "raw"}],
    ids=["no-namespaces", "string-item", "non-string-part", "string-list"],
)
def test_namespace_listing_of_the_wrong_shape_is_unavailable(body: dict[str, Any]):
    """A listed namespace must be a list of strings; anything else is a 502, not a tuple of characters."""
    stub = PolarisStub()
    stub.on("GET", NAMESPACES, httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="the namespaces of catalog sales in a form this backend"):
        NamespacesPolarisRepo(stub.client()).list_in(CatalogId.of("sales"), ())


@pytest.mark.parametrize(
    ("status", "error"),
    [(409, ConflictError), (400, ValidationError), (404, NotFoundError), (500, CatalogUnavailableError)],
)
def test_updates_failing_after_applied_removals_say_the_removals_were_applied(status: int, error: type[Exception]):
    """The removals already landed, so the error keeps its type (and status) and says to reload."""
    stub = PolarisStub()
    stub.on(
        "POST",
        f"{NAMESPACES}/raw/properties",
        httpx.Response(200, json={"updated": [], "removed": ["stale"], "missing": []}),
        _error(status, "Concurrent modification of namespace: raw"),
    )

    with pytest.raises(error) as raised:
        NamespacesPolarisRepo(stub.client()).update_properties(_RAW, {"tier": "gold"}, ["stale"])

    assert type(raised.value) is error
    assert str(raised.value).startswith("removals were applied; reload and retry: ")
    assert "Concurrent modification of namespace: raw" in str(raised.value)


def test_failing_removals_are_reported_unchanged():
    """When the first request fails nothing was applied, so its error passes through as is."""
    stub = PolarisStub()
    stub.on("POST", f"{NAMESPACES}/raw/properties", _error(409, "Concurrent modification of namespace: raw"))

    with pytest.raises(ConflictError) as raised:
        NamespacesPolarisRepo(stub.client()).update_properties(_RAW, {"tier": "gold"}, ["stale"])

    assert "removals were applied" not in str(raised.value)
    assert len(stub.requests) == 1


def test_failing_updates_without_removals_are_reported_unchanged():
    """With no removals sent, a failed update applied nothing, so its error passes through as is."""
    stub = PolarisStub()
    stub.on("POST", f"{NAMESPACES}/raw/properties", _error(409, "Concurrent modification of namespace: raw"))

    with pytest.raises(ConflictError) as raised:
        NamespacesPolarisRepo(stub.client()).update_properties(_RAW, {"tier": "gold"}, [])

    assert "removals were applied" not in str(raised.value)


@pytest.mark.parametrize(
    "properties",
    [[], "", {"owner": 1}, {"owner": None}, [["owner", "de"]]],
    ids=["empty-list", "empty-text", "number-value", "null-value", "list-of-pairs"],
)
def test_ill_typed_value_from_polaris_is_unavailable(properties: object):
    """Properties that are not an object of text values are refused, never coerced to text or emptied."""
    stub = PolarisStub()
    stub.on("GET", f"{NAMESPACES}/raw", httpx.Response(200, json={"namespace": ["raw"], "properties": properties}))

    with pytest.raises(CatalogUnavailableError, match="namespace \\['raw'\\] in a form this backend cannot read"):
        NamespacesPolarisRepo(stub.client()).get(NamespaceId.of("sales", ("raw",)))


@pytest.mark.parametrize("body", [{"namespace": ["raw"]}, {"namespace": ["raw"], "properties": None}])
def test_absent_or_null_properties_from_polaris_are_empty(body: dict[str, Any]):
    """A reply without properties, or with null ones, reads as no properties, as before."""
    stub = PolarisStub()
    stub.on("GET", f"{NAMESPACES}/raw", httpx.Response(200, json=body))

    namespace = NamespacesPolarisRepo(stub.client()).get(NamespaceId.of("sales", ("raw",)))

    assert namespace is not None
    assert namespace.properties == {}


def test_write_request_bytes_are_unchanged():
    """The create and properties bodies are byte for byte what they were before the domain moved to Pydantic."""
    stub = PolarisStub()
    stub.on(
        "POST", NAMESPACES, httpx.Response(200, json={"namespace": ["retail", "a.b"], "properties": {"owner": "x"}})
    )
    stub.on("POST", f"{NAMESPACES}/retail/properties", httpx.Response(200, json={}), httpx.Response(200, json={}))
    stub.on("GET", f"{NAMESPACES}/retail", httpx.Response(200, json={"namespace": ["retail"], "properties": {}}))
    repo = NamespacesPolarisRepo(stub.client())

    repo.create(Namespace(id=NamespaceId.of("sales", ("retail", "a.b")), properties={"owner": "x"}))
    repo.update_properties(NamespaceId.of("sales", ("retail",)), {"tier": "gold"}, ["stale"])

    assert [request.content for request in stub.requests] == [
        b'{"namespace":["retail","a.b"],"properties":{"owner":"x"}}',
        b'{"removals":["stale"]}',
        b'{"updates":{"tier":"gold"}}',
        b"",
    ]
