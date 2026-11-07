"""Test the namespace routes."""

from __future__ import annotations

from context.catalog.application.exceptions import ConflictError, NotFoundError
from context.catalog.application.port.inbound.namespace import (
    CreateNamespaceUseCaseInput,
    CreateNamespaceUseCaseOutput,
    DeleteNamespaceUseCaseInput,
    DeleteNamespaceUseCaseOutput,
    GetNamespaceUseCaseInput,
    GetNamespaceUseCaseOutput,
    ListNamespacesUseCaseInput,
    ListNamespacesUseCaseOutput,
    ListNamespacesUseCaseOutputItem,
    UpdateNamespacePropertiesUseCaseInput,
    UpdateNamespacePropertiesUseCaseOutput,
)
from context.catalog.application.service.namespace import (
    CreateNamespaceService,
    GetNamespaceService,
    ListNamespacesService,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client
from tests.context.catalog.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo

BASE = "/v1/catalogs/sales/namespaces"


def test_create_namespace_returns_201():
    """Creating a namespace returns 201 and passes the form to the use case."""
    stub = StubUseCase(CreateNamespaceUseCaseOutput("sales", ["raw"], {"owner": "de"}))
    client = build_client(create_namespace=stub)

    response = client.post(BASE, json={"namespace": ["raw"], "properties": {"owner": "de"}})

    assert response.status_code == 201
    assert response.json() == {"catalog": "sales", "namespace": ["raw"], "properties": {"owner": "de"}}
    assert stub.requests == [CreateNamespaceUseCaseInput("sales", ["raw"], {"owner": "de"})]


def test_create_namespace_rejects_unknown_fields():
    """A body field the form does not have is refused."""
    stub = StubUseCase()
    response = build_client(create_namespace=stub).post(BASE, json={"namespace": ["raw"], "purge": True})

    assert response.status_code == 422
    assert stub.requests == []


def test_list_namespaces_passes_parent_split_on_the_unit_separator():
    """``parent`` is the parts joined by U+001F; an absent one lists the top level."""
    stub = StubUseCase(ListNamespacesUseCaseOutput([ListNamespacesUseCaseOutputItem("sales", ["a", "b.c"])]))
    client = build_client(list_namespaces=stub)

    top = client.get(BASE)
    nested = client.get(BASE, params={"parent": "a\x1fx.y"})

    assert top.json() == [{"catalog": "sales", "namespace": ["a", "b.c"]}]
    assert nested.status_code == 200
    assert stub.requests == [
        ListNamespacesUseCaseInput("sales", []),
        ListNamespacesUseCaseInput("sales", ["a", "x.y"]),
    ]


def test_namespace_path_uses_unit_separator():
    """``a%1Fb`` in the path is the two parts a and b; ``a.b`` is one part."""
    stub = StubUseCase(GetNamespaceUseCaseOutput("sales", ["a", "b"], {}))
    client = build_client(get_namespace=stub)

    nested = client.get(f"{BASE}/a%1Fb")
    dotted = client.get(f"{BASE}/a.b")

    assert nested.json()["namespace"] == ["a", "b"]
    assert dotted.status_code == 200
    assert stub.requests == [GetNamespaceUseCaseInput("sales", ["a", "b"]), GetNamespaceUseCaseInput("sales", ["a.b"])]


def test_namespace_part_with_dot_round_trips():
    """A dotted part created through the API is listed with the same single part."""
    repo = InMemoryNamespacesRepo()
    client = build_client(
        create_namespace=CreateNamespaceService(repo),
        get_namespace=GetNamespaceService(repo),
        list_namespaces=ListNamespacesService(repo),
    )

    created = client.post(BASE, json={"namespace": ["a.b"]})
    fetched = client.get(f"{BASE}/a.b")
    listed = client.get(BASE)

    assert created.json()["namespace"] == ["a.b"]
    assert fetched.json()["namespace"] == ["a.b"]
    assert listed.json() == [{"catalog": "sales", "namespace": ["a.b"]}]


def test_get_unknown_namespace_is_404():
    """A missing namespace is a 404 with the message."""
    client = build_client(get_namespace=StubUseCase(error=NotFoundError("Namespace does not exist: x")))

    response = client.get(f"{BASE}/x")

    assert (response.status_code, response.json()) == (404, {"detail": "Namespace does not exist: x"})


def test_delete_namespace_returns_204():
    """Delete returns 204 with no body."""
    stub = StubUseCase(DeleteNamespaceUseCaseOutput())

    response = build_client(delete_namespace=stub).delete(f"{BASE}/a%1Fb")

    assert response.status_code == 204
    assert stub.requests == [DeleteNamespaceUseCaseInput("sales", ["a", "b"])]


def test_delete_non_empty_namespace_is_409_with_polaris_message():
    """Polaris refusing a non-empty namespace is a 409 carrying its message."""
    client = build_client(delete_namespace=StubUseCase(error=ConflictError("Namespace raw is not empty")))

    response = client.delete(f"{BASE}/raw")

    assert (response.status_code, response.json()) == (409, {"detail": "Namespace raw is not empty"})


def test_update_namespace_properties():
    """PUT /properties passes updates and removals and returns the namespace."""
    stub = StubUseCase(UpdateNamespacePropertiesUseCaseOutput("sales", ["a", "b"], {"tier": "gold"}))

    response = build_client(update_namespace_properties=stub).put(
        f"{BASE}/a%1Fb/properties", json={"updates": {"tier": "gold"}, "removals": ["stale"]}
    )

    assert response.status_code == 200
    assert response.json()["properties"] == {"tier": "gold"}
    assert stub.requests == [UpdateNamespacePropertiesUseCaseInput("sales", ["a", "b"], {"tier": "gold"}, ["stale"])]


def test_update_namespace_properties_defaults_to_no_changes():
    """Both lists are optional and default to empty."""
    stub = StubUseCase(UpdateNamespacePropertiesUseCaseOutput("sales", ["raw"], {}))

    build_client(update_namespace_properties=stub).put(f"{BASE}/raw/properties", json={})

    assert stub.requests == [UpdateNamespacePropertiesUseCaseInput("sales", ["raw"], {}, [])]
